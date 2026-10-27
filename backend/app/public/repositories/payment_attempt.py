from uuid import UUID

from sqlalchemy import Row, text

from app.db.repository import Repository
from app.db.models import PaymentAttempt


class PaymentAttemptRepository(Repository):
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
        # The Stripe account is the database's (trg_payment_attempts_account).
        self.db.refresh(record)

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

    def lock_by_id(
        self,
        *,
        id: UUID,
    ) -> PaymentAttempt | None:
        """
        The attempt, locked until this transaction ends, read fresh: two
        settlers (a webhook and the success page) queue here, and the second
        sees what the first decided.
        """
        return (
            self.db.query(PaymentAttempt)
            .filter(PaymentAttempt.id == id)
            .populate_existing()
            .with_for_update()
            .first()
        )

    def list_pending_checkouts(self) -> list[Row]:
        """
        Every business's attempts still waiting on Stripe, for the scheduled
        payment check (public.pending_checkouts; its channel must be set).
        """
        return self.db.execute(
            text("SELECT payment_attempt_id, user_id, location_id FROM public.pending_checkouts()")
        ).all()

    def get_latest_by_booking_group_id(
        self,
        *,
        booking_group_id: UUID,
    ) -> PaymentAttempt | None:
        return (
            self.db.query(PaymentAttempt)
            .filter(PaymentAttempt.booking_group_id == booking_group_id)
            .order_by(PaymentAttempt.created_at.desc())
            .first()
        )

    def get_by_checkout_session_id(
        self,
        *,
        checkout_session_id: str,
    ) -> PaymentAttempt | None:
        return (
            self.db.query(PaymentAttempt)
            .filter(PaymentAttempt.stripe_checkout_session_id == checkout_session_id)
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