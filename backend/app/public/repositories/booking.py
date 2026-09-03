from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.booking import Booking


class BookingRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        booking_group_id: UUID,
        location_service_id: UUID,
        child_id: UUID,
        price_snapshot_cents: int,
        currency: str,
        payment_status: str = "PENDING",
        cancelled_at=None,
    ) -> Booking:
        record = Booking(
            location_id=location_id,
            user_id=user_id,
            booking_group_id=booking_group_id,
            location_service_id=location_service_id,
            child_id=child_id,
            payment_status=payment_status,
            cancelled_at=cancelled_at,
            price_snapshot_cents=price_snapshot_cents,
            currency=currency,
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
