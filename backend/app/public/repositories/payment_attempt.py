from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.payment_attempt import PaymentAttempt


class PaymentAttemptRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        booking_group_id: UUID,
        total_cents: int,
        currency: str,
        stripe_status: str = "PENDING",
        stripe_payment_intent_id: str | None = None,
        stripe_checkout_session_id: str | None = None,
        stripe_receipt_url: str | None = None,
    ) -> PaymentAttempt:
        record = PaymentAttempt(
            location_id=location_id,
            user_id=user_id,
            booking_group_id=booking_group_id,
            total_cents=total_cents,
            currency=currency,
            stripe_status=stripe_status,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_checkout_session_id=stripe_checkout_session_id,
            stripe_receipt_url=stripe_receipt_url,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> PaymentAttempt | None:
        return (
            self.db.query(PaymentAttempt)
            .filter(PaymentAttempt.id == id)
            .first()
        )

    def get_successful_by_booking_group_id(
        self,
        *,
        booking_group_id: UUID
    ) -> PaymentAttempt | None:
        return (
            self.db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.booking_group_id == booking_group_id,
                PaymentAttempt.stripe_status == "SUCCEEDED",
            )
            .first()
        )