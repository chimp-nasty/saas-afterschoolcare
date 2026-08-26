from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.booking_refund import BookingRefund


class BookingRefundRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        booking_id: UUID,
        invoice_id: UUID,
        invoice_booking_item_id: UUID,
        parent_id: UUID,
        requested_by_user_id: UUID,
        amount_cents: int,
        currency: str,
        stripe_payment_intent_id: str,
        status: str = "PENDING",
        reason: str | None = None,
        stripe_refund_id: str | None = None,
        processed_at: datetime | None = None,
        failed_at: datetime | None = None,
        failure_reason: str | None = None,
    ) -> BookingRefund:
        record = BookingRefund(
            booking_id=booking_id,
            invoice_id=invoice_id,
            invoice_booking_item_id=invoice_booking_item_id,
            parent_id=parent_id,
            requested_by_user_id=requested_by_user_id,
            amount_cents=amount_cents,
            currency=currency,
            stripe_payment_intent_id=stripe_payment_intent_id,
            status=status,
            reason=reason,
            stripe_refund_id=stripe_refund_id,
            processed_at=processed_at,
            failed_at=failed_at,
            failure_reason=failure_reason,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> BookingRefund | None:
        return (
            self.db.query(BookingRefund)
            .filter(BookingRefund.id == id)
            .first()
        )
