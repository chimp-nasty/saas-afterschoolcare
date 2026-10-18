import logging
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.db.transaction import transactional
from app.errors.payments import InvalidWebhookError
from app.integrations.payments.stripe.client import StripeClient
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.schemas.enums import BookingStatus, PaymentStatus, StripeStatus


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
    ):
        self.db = db
        self.rls_context = rls_context
        self.payment_attempt_repository = payment_attempt_repository
        self.booking_repository = booking_repository
        self.stripe = StripeClient()

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
