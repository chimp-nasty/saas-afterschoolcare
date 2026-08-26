from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.booking import Booking


class BookingRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        parent_id: UUID,
        child_id: UUID,
        location_service_day_id: UUID,
        booking_status_id: int,
        payment_status_id: int,
        price_snapshot_cents: int,
        currency: str,
        booking_group_id: UUID | None = None,
        cancelled_at: datetime | None = None,
        cancellation_reason: str | None = None,
    ) -> Booking:
        record = Booking(
            parent_id=parent_id,
            child_id=child_id,
            location_service_day_id=location_service_day_id,
            booking_status_id=booking_status_id,
            payment_status_id=payment_status_id,
            price_snapshot_cents=price_snapshot_cents,
            currency=currency,
            booking_group_id=booking_group_id,
            cancelled_at=cancelled_at,
            cancellation_reason=cancellation_reason,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Booking | None:
        return (
            self.db.query(Booking)
            .filter(Booking.id == id)
            .first()
        )
