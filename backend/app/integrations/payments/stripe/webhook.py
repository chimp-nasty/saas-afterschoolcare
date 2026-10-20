import logging
from datetime import datetime, timezone
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.auth.repositories.user import UserRepository
from app.db.transaction import transactional
from app.errors.payments import InvalidWebhookError, PaymentProviderError
from app.integrations.email.messages import (
    BookingConfirmationEmail,
    RefundConfirmationEmail,
    short_reference,
)
from app.integrations.email.outbox import EmailOutbox
from app.integrations.payments.stripe.client import StripeClient
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.repositories.refund import RefundRepository
from app.public.schemas.enums import BookingStatus, PaymentStatus, RefundStatus, StripeStatus


logger = logging.getLogger("app.payments")


class StripeWebhookService:
    """
    The only place payment state changes. The success redirect just reads
    it (ReadBookingService.get_checkout_status), because a user can close
    the tab before it loads or open it without paying.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        payment_attempt_repository: PaymentAttemptRepository,
        booking_repository: BookingRepository,
        refund_repository: RefundRepository,
        user_repository: UserRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.payment_attempt_repository = payment_attempt_repository
        self.booking_repository = booking_repository
        self.refund_repository = refund_repository
        self.user_repository = user_repository
        self.stripe = StripeClient()
        self.emails = EmailOutbox(db)

    def handle(
        self,
        *,
        payload: bytes,
        signature: str | None,
    ) -> None:
        try:
            event = self.stripe.construct_webhook_event(
                payload=payload,
                signature=signature or "",
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise InvalidWebhookError(log_reason=str(exc)) from exc

        event_type = event["type"]
        session = event["data"]["object"]

        if event_type == "checkout.session.completed":
            # Card payments are "paid" here; delayed methods (e.g. bank
            # debits) settle later via the async_payment_* events.
            if session["payment_status"] == "paid":
                self._settle(session=session, succeeded=True)

        elif event_type == "checkout.session.async_payment_succeeded":
            self._settle(session=session, succeeded=True)

        elif event_type in (
            "checkout.session.expired",
            "checkout.session.async_payment_failed",
        ):
            self._settle(session=session, succeeded=False)

        # A Refund object; its status says how far it's got.
        elif event_type in (
            "refund.created",
            "refund.updated",
            "refund.failed",
        ):
            self._settle_refund(stripe_refund=session)

        # Anything else is acknowledged and ignored.

    @transactional
    def _settle(
        self,
        *,
        session,
        succeeded: bool,
    ) -> None:
        metadata = session.get("metadata") or {}

        if "payment_attempt_id" not in metadata:
            logger.warning(
                "Stripe checkout without our metadata",
                extra={
                    "event": "stripe_webhook_unmatched",
                    "result": "ignored",
                    "reason": session.get("id"),
                },
            )
            return

        # A webhook has no logged-in user, so act as the booking's user at
        # its location; RLS then applies as it would for them. The metadata
        # is trusted because the signature was verified.
        self.rls_context.set_user_id(user_id=UUID(metadata["user_id"]))
        self.rls_context.set_location_id(location_id=UUID(metadata["location_id"]))

        attempt = self.payment_attempt_repository.get_by_id(
            id=UUID(metadata["payment_attempt_id"]),
        )

        # Stripe retries deliveries; only a PENDING attempt moves.
        if not attempt or attempt.stripe_status != StripeStatus.PENDING:
            return

        attempt.stripe_status = (
            StripeStatus.SUCCEEDED if succeeded else StripeStatus.FAILED
        )

        if session.get("payment_intent"):
            attempt.stripe_payment_intent_id = session["payment_intent"]

        if succeeded:
            attempt.paid_at = datetime.now(timezone.utc)

            if attempt.stripe_payment_intent_id:
                attempt.stripe_receipt_url = self._receipt_url(
                    payment_intent_id=attempt.stripe_payment_intent_id,
                )

            confirmed = self.booking_repository.settle_pending_for_group(
                booking_group_id=attempt.booking_group_id,
                booking_status=BookingStatus.CONFIRMED,
                payment_status=PaymentStatus.PAID,
            )

            # Paid, but the bookings were already released (cancelled, or
            # their hold lapsed before this webhook arrived). The money was
            # taken for nothing: this needs a refund.
            if confirmed == 0:
                logger.error(
                    "Payment received for bookings that are no longer pending",
                    extra={
                        "event": "stripe_paid_without_bookings",
                        "result": "refund_required",
                        "reason": (
                            f"payment_attempt_id={attempt.id}; "
                            f"booking_group_id={attempt.booking_group_id}; "
                            f"checkout_session_id={session.get('id')}"
                        ),
                    },
                )

                return

            # Only here once per payment: a repeated event finds the attempt
            # no longer pending and stops above.
            family = self.user_repository.get_by_id(id=attempt.user_id)

            self.emails.queue(BookingConfirmationEmail(
                location_id=attempt.location_id,
                user_id=family.id,
                to_email=family.email,
                first_name=family.first_name,
                reference=short_reference("BK", attempt.booking_group_id),
                total_cents=attempt.total_cents,
                currency=attempt.currency,
            ))

            return

        # A resumed checkout makes a newer attempt for the same bookings;
        # the old session expiring must not release them.
        latest = self.payment_attempt_repository.get_latest_by_booking_group_id(
            booking_group_id=attempt.booking_group_id,
        )

        if latest and latest.id == attempt.id:
            self.booking_repository.settle_pending_for_group(
                booking_group_id=attempt.booking_group_id,
                booking_status=BookingStatus.EXPIRED,
                payment_status=PaymentStatus.FAILED,
            )

    def _receipt_url(
        self,
        *,
        payment_intent_id: str,
    ) -> str | None:
        """
        The payment's receipt link, if Stripe can give it now. A failed
        lookup never stops the payment settling: the booking page just
        goes without "View receipt".
        """
        try:
            return self.stripe.get_receipt_url(payment_intent_id=payment_intent_id)
        except PaymentProviderError as exc:
            logger.warning(
                "Couldn't fetch the Stripe receipt",
                extra={
                    "event": "stripe_receipt_unavailable",
                    "result": "skipped",
                    "reason": f"payment_intent_id={payment_intent_id}; {exc.log_reason}",
                },
            )
            return None

    @transactional
    def _settle_refund(
        self,
        *,
        stripe_refund,
    ) -> None:
        """
        Finish one of our refunds. Succeeded: cancel the booking (releasing
        its place) and mark the refund processed. Failed or canceled: record
        it, so the family or staff can try again. Pending and
        requires_action wait for a later event.
        """
        metadata = stripe_refund.get("metadata") or {}

        # Refunds made by hand in the Stripe dashboard aren't ours to settle.
        if "refund_id" not in metadata:
            logger.warning(
                "Stripe refund without our metadata",
                extra={
                    "event": "stripe_refund_unmatched",
                    "result": "ignored",
                    "reason": stripe_refund.get("id"),
                },
            )
            return

        self.rls_context.set_user_id(user_id=UUID(metadata["user_id"]))
        self.rls_context.set_location_id(location_id=UUID(metadata["location_id"]))

        refund = self.refund_repository.get_by_id(id=UUID(metadata["refund_id"]))

        # Stripe retries and sends several events per refund; only a
        # pending refund moves.
        if not refund or refund.status != RefundStatus.PENDING:
            return

        # Saving Stripe's reply may have failed after the refund was made.
        if not refund.stripe_refund_id:
            self.refund_repository.mark_submitted(
                refund=refund,
                stripe_refund_id=stripe_refund["id"],
            )

        status = stripe_refund.get("status")

        if status == "succeeded":
            self.refund_repository.mark_succeeded(refund=refund)
            self.booking_repository.mark_refunded(booking_id=refund.booking_id)

            logger.info(
                "Refund completed",
                extra={
                    "event": "refund_completed",
                    "result": "success",
                    "reason": f"refund_id={refund.id}; booking_id={refund.booking_id}",
                },
            )

            # Once per refund: a repeated event finds it no longer pending.
            family = self.user_repository.get_by_id(id=refund.user_id)

            self.emails.queue(RefundConfirmationEmail(
                location_id=refund.location_id,
                user_id=family.id,
                to_email=family.email,
                first_name=family.first_name,
                reference=short_reference("RF", refund.id),
                amount_cents=refund.amount_cents,
                currency=refund.currency,
            ))

        elif status in ("failed", "canceled"):
            self.refund_repository.mark_failed(
                refund=refund,
                failure_reason=stripe_refund.get("failure_reason") or f"Stripe refund {status}",
            )

            logger.warning(
                "Refund failed",
                extra={
                    "event": "refund_failed",
                    "result": "failed",
                    "reason": f"refund_id={refund.id}; status={status}",
                },
            )
