from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import PaymentAttempt, Refund, TenantStripeAccount
from app.public.schemas.enums import RefundStatus


class RefundRepository(Repository):
    def create(
        self,
        *,
        booking_id: UUID,
        location_id: UUID,
        user_id: UUID,
        requested_by_user_id: UUID,
        reason: str | None = None,
    ) -> Refund:
        """
        A pending refund. trg_refunds_rules (schema/0004) refuses one the
        booking isn't eligible for, and fills in the amount, currency and
        payment from the booking.
        """
        record = Refund(
            booking_id=booking_id,
            location_id=location_id,
            user_id=user_id,
            requested_by_user_id=requested_by_user_id,
            reason=reason,
        )

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Refund | None:
        return (
            self.db.query(Refund)
            .filter(Refund.id == id)
            .first()
        )

    def get_payment(
        self,
        *,
        refund: Refund,
    ) -> Row:
        """
        The payment being refunded: its payment intent, the Stripe account it
        was taken in (refunds go through the same one), and whether that
        account has since revoked our access.
        """
        return (
            self.db.query(
                PaymentAttempt.stripe_payment_intent_id,
                PaymentAttempt.stripe_account_id,
                TenantStripeAccount.revoked_at.isnot(None).label("account_revoked"),
            )
            .outerjoin(
                TenantStripeAccount,
                TenantStripeAccount.stripe_account_id == PaymentAttempt.stripe_account_id,
            )
            .filter(PaymentAttempt.id == refund.payment_attempt_id)
            .one()
        )

    def mark_submitted(
        self,
        *,
        refund: Refund,
        stripe_refund_id: str,
    ) -> Refund:
        refund.stripe_refund_id = stripe_refund_id

        self.db.flush()

        return refund

    def mark_succeeded(
        self,
        *,
        refund: Refund,
    ) -> Refund:
        refund.status = RefundStatus.SUCCEEDED
        refund.processed_at = datetime.now(timezone.utc)

        self.db.flush()

        return refund

    def mark_failed(
        self,
        *,
        refund: Refund,
        failure_reason: str,
    ) -> Refund:
        refund.status = RefundStatus.FAILED
        refund.failed_at = datetime.now(timezone.utc)
        refund.failure_reason = failure_reason

        self.db.flush()

        return refund
