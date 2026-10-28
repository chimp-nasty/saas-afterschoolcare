import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.db.transaction import transactional
from app.errors.bookings import BookingNotFoundError
from app.errors.payments import PaymentProviderError, StripeAccountRevokedError
from app.integrations.payments.stripe.client import StripeClient
from app.public.repositories.booking import BookingRepository
from app.public.repositories.refund import RefundRepository
from app.public.schemas.refunds import RefundResponse


logger = logging.getLogger("app.payments")


@dataclass
class _OpenedRefund:
    refund_id: UUID
    reference: str
    booking_id: UUID
    family_user_id: UUID
    location_id: UUID
    amount_cents: int
    payment_intent_id: str
    # The tenant's Stripe account the payment was taken in (None: the platform's).
    stripe_account_id: str | None


class CreateRefundService:
    """
    Refund one booking: record a pending refund, send it to Stripe, and
    leave the outcome to the webhook (StripeWebhookService), which cancels
    the booking and releases its place once the money has gone back.

    Each step is its own transaction, so no database transaction stays open
    during the Stripe call. If saving Stripe's reply fails, the webhook still
    finds the refund through the refund_id in its metadata.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        booking_repository: BookingRepository,
        refund_repository: RefundRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.booking_repository = booking_repository
        self.refund_repository = refund_repository

    def create(
        self,
        *,
        booking_id: UUID,
        user_id: UUID,
        location_id: UUID,
        kiosk_device_id: UUID | None = None,
    ) -> RefundResponse:
        """
        Refund one booking (one child, one day) in full. From the staff kiosk,
        `kiosk_device_id` keeps each later step on the kiosk channel too.
        """
        self.kiosk_device_id = kiosk_device_id

        opened = self._open(
            booking_id=booking_id,
            requested_by_user_id=user_id,
        )

        try:
            stripe_refund = StripeClient(account_id=opened.stripe_account_id).create_refund(
                payment_intent_id=opened.payment_intent_id,
                amount_cents=opened.amount_cents,
                # The webhook acts as the booking's family, at its location.
                metadata={
                    "reference": opened.reference,
                    "refund_id": str(opened.refund_id),
                    "booking_id": str(opened.booking_id),
                    "user_id": str(opened.family_user_id),
                    "location_id": str(opened.location_id),
                },
                idempotency_key=f"refund:{opened.refund_id}",
            )
        except PaymentProviderError as exc:
            # Recorded as failed, so it can be tried again.
            self._record_failure(
                refund_id=opened.refund_id,
                user_id=user_id,
                location_id=location_id,
                failure_reason=exc.log_reason or exc.message,
            )
            raise

        return self._record_submission(
            refund_id=opened.refund_id,
            user_id=user_id,
            location_id=location_id,
            stripe_refund_id=stripe_refund.refund_id,
            stripe_status=stripe_refund.status,
        )

    @transactional
    def _open(
        self,
        *,
        booking_id: UUID,
        requested_by_user_id: UUID,
    ) -> _OpenedRefund:
        # RLS: a family sees only their own bookings, staff their location's.
        booking = self.booking_repository.get_by_id(id=booking_id)

        if not booking:
            raise BookingNotFoundError()

        # The window, one active refund per booking, the amount and the
        # payment are all decided by the database (schema/0004).
        refund = self.refund_repository.create(
            booking_id=booking.id,
            location_id=booking.location_id,
            user_id=booking.user_id,
            requested_by_user_id=requested_by_user_id,
        )

        logger.info(
            "Refund requested",
            extra={
                "event": "refund_requested",
                "result": "pending",
                "reason": f"refund_id={refund.id}; booking_id={booking.id}; amount_cents={refund.amount_cents}",
            },
        )

        payment = self.refund_repository.get_payment(refund=refund)

        # The centre removed our access in Stripe: only they can refund it
        # now (in their dashboard). Raising undoes the refund row.
        if payment.account_revoked:
            raise StripeAccountRevokedError()

        return _OpenedRefund(
            refund_id=refund.id,
            reference=refund.reference,
            booking_id=booking.id,
            family_user_id=booking.user_id,
            location_id=booking.location_id,
            amount_cents=refund.amount_cents,
            payment_intent_id=payment.stripe_payment_intent_id,
            stripe_account_id=payment.stripe_account_id,
        )

    @transactional
    def _record_submission(
        self,
        *,
        refund_id: UUID,
        user_id: UUID,
        location_id: UUID,
        stripe_refund_id: str,
        stripe_status: str,
    ) -> RefundResponse:
        self._restore_rls(user_id=user_id, location_id=location_id)

        refund = self.refund_repository.get_by_id(id=refund_id)

        self.refund_repository.mark_submitted(
            refund=refund,
            stripe_refund_id=stripe_refund_id,
        )

        # Stripe can refuse straight away (rare for card refunds); a
        # success still waits for the webhook, which settles the booking.
        if stripe_status in ("failed", "canceled"):
            self.refund_repository.mark_failed(
                refund=refund,
                failure_reason=f"Stripe returned {stripe_status}",
            )

        return RefundResponse.model_validate(refund, from_attributes=True)

    @transactional
    def _record_failure(
        self,
        *,
        refund_id: UUID,
        user_id: UUID,
        location_id: UUID,
        failure_reason: str,
    ) -> None:
        self._restore_rls(user_id=user_id, location_id=location_id)

        refund = self.refund_repository.get_by_id(id=refund_id)

        self.refund_repository.mark_failed(
            refund=refund,
            failure_reason=failure_reason,
        )

        logger.warning(
            "Refund failed to reach Stripe",
            extra={
                "event": "refund_failed",
                "result": "failed",
                "reason": f"refund_id={refund_id}; {failure_reason}",
            },
        )

    def _restore_rls(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        # The RLS settings last one transaction; each later step sets them
        # again for the same user and location.
        self.rls_context.set_user_id(user_id=user_id)
        self.rls_context.set_location_id(location_id=location_id)

        if getattr(self, "kiosk_device_id", None):
            self.rls_context.set_kiosk_channel(device_id=self.kiosk_device_id)
