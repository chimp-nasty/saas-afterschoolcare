import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.auth.repositories.user import UserRepository
from app.db.models import PaymentAttempt
from app.db.session import SessionLocal
from app.db.transaction import transactional
from app.errors.payments import PaymentProviderError
from app.integrations.email.messages import BookingConfirmationEmail, short_reference
from app.integrations.email.outbox import EmailOutbox
from app.integrations.payments.stripe.client import StripeCheckout, StripeClient
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.schemas.enums import BookingStatus, PaymentStatus, StripeStatus


logger = logging.getLogger("app.payments")


def is_paid(checkout: StripeCheckout) -> bool:
    """
    Stripe has the money. A completed checkout paid by a delayed method
    (e.g. bank debit) is "unpaid" until its async_payment_* event.
    """
    return checkout.status == "complete" and checkout.payment_status == "paid"


class PaymentSettlementService:
    """
    Moves a pending payment attempt to its final state: the webhook's events,
    and asking Stripe directly when the webhook may have been missed (the
    success page, cancelling, continuing to payment, the scheduled payment
    check; docs/payment-confirmation.md). Whichever arrives first settles it;
    the attempt is locked and only a PENDING one moves, so the rest change
    nothing and no second email goes out.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        payment_attempt_repository: PaymentAttemptRepository,
        booking_repository: BookingRepository,
        user_repository: UserRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.payment_attempt_repository = payment_attempt_repository
        self.booking_repository = booking_repository
        self.user_repository = user_repository
        self.emails = EmailOutbox(db)

    @classmethod
    def on(cls, db: Session) -> "PaymentSettlementService":
        return cls(
            db=db,
            rls_context=RlsContextRepository(db=db),
            payment_attempt_repository=PaymentAttemptRepository(db=db),
            booking_repository=BookingRepository(db=db),
            user_repository=UserRepository(db=db),
        )

    def lock_pending(
        self,
        *,
        payment_attempt_id: UUID,
        user_id: UUID,
        location_id: UUID,
    ) -> PaymentAttempt | None:
        """
        The attempt, locked for this transaction, if it's still PENDING. Acts
        as its family at its location, so RLS applies as it would for them.
        """
        self.rls_context.set_user_id(user_id=user_id)
        self.rls_context.set_location_id(location_id=location_id)

        attempt = self.payment_attempt_repository.lock_by_id(id=payment_attempt_id)

        if not attempt or attempt.stripe_status != StripeStatus.PENDING:
            return None

        return attempt

    def reconcile(
        self,
        *,
        attempt: PaymentAttempt,
        settle_expired: bool,
    ) -> StripeCheckout:
        """
        Ask Stripe about a pending attempt's checkout and settle it if it's
        paid; if Stripe expired it, only with `settle_expired` (resuming
        opens a new checkout for the same bookings instead). Raises
        PaymentProviderError if Stripe can't be reached.
        """
        checkout = StripeClient(account_id=attempt.stripe_account_id).get_checkout_session(
            checkout_session_id=attempt.stripe_checkout_session_id,
        )

        if is_paid(checkout):
            self.settle(attempt=attempt, succeeded=True, payment_intent_id=checkout.payment_intent_id)

            logger.warning(
                "Payment confirmed without its webhook",
                extra={
                    "event": "stripe_payment_reconciled",
                    "result": "success",
                    "reason": f"payment_attempt_id={attempt.id}",
                },
            )

        elif checkout.status == "expired" and settle_expired:
            self.settle(attempt=attempt, succeeded=False, payment_intent_id=None)

        return checkout

    @transactional
    def confirm(
        self,
        *,
        payment_attempt_id: UUID,
        user_id: UUID,
        location_id: UUID,
    ) -> StripeCheckout | None:
        """
        reconcile() in a transaction of its own, so a payment found on Stripe
        stays settled even when the request that found it is then refused
        ("already paid"). None if the attempt has already settled.
        """
        attempt = self.lock_pending(
            payment_attempt_id=payment_attempt_id,
            user_id=user_id,
            location_id=location_id,
        )

        if not attempt:
            return None

        return self.reconcile(attempt=attempt, settle_expired=False)

    def settle(
        self,
        *,
        attempt: PaymentAttempt,
        succeeded: bool,
        payment_intent_id: str | None,
    ) -> None:
        """Settle a locked PENDING attempt, in the caller's transaction."""
        attempt.stripe_status = (
            StripeStatus.SUCCEEDED if succeeded else StripeStatus.FAILED
        )

        if payment_intent_id:
            attempt.stripe_payment_intent_id = payment_intent_id

        if succeeded:
            attempt.paid_at = datetime.now(timezone.utc)

            if attempt.stripe_payment_intent_id:
                attempt.stripe_receipt_url = self._receipt_url(
                    payment_intent_id=attempt.stripe_payment_intent_id,
                    account_id=attempt.stripe_account_id,
                )

            confirmed = self.booking_repository.settle_pending_for_group(
                booking_group_id=attempt.booking_group_id,
                booking_status=BookingStatus.CONFIRMED,
                payment_status=PaymentStatus.PAID,
            )

            # Paid, but the bookings were already released (cancelled, or
            # their hold lapsed before the payment was seen). The money was
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
                            f"checkout_session_id={attempt.stripe_checkout_session_id}"
                        ),
                    },
                )

                return

            # Only here once per payment: anything later finds the attempt
            # no longer pending.
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
        account_id: str | None,
    ) -> str | None:
        """
        The payment's receipt link, if Stripe can give it now. A failed
        lookup never stops the payment settling: the booking page just
        goes without "View receipt".
        """
        try:
            return StripeClient(account_id=account_id).get_receipt_url(payment_intent_id=payment_intent_id)
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


def confirm_with_stripe(attempt: PaymentAttempt) -> StripeCheckout | None:
    """
    Ask Stripe whether a pending attempt has been paid, and settle it if so,
    on a session of its own: committed whatever the caller's transaction
    does next. None if it has already settled.
    """
    db = SessionLocal()

    try:
        return PaymentSettlementService.on(db).confirm(
            payment_attempt_id=attempt.id,
            user_id=attempt.user_id,
            location_id=attempt.location_id,
        )
    finally:
        db.close()
