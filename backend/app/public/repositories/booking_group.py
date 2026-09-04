from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.booking_group import BookingGroup
from app.public.models.booking import Booking


class BookingGroupRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        idempotency_key: str,
        user_id: UUID,
        source: str | None = None,
    ) -> BookingGroup:
        record = BookingGroup(
            idempotency_key=idempotency_key,
            user_id=user_id,
            source=source,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> BookingGroup | None:
        return (
            self.db.query(BookingGroup)
            .filter(BookingGroup.id == id)
            .first()
        )

    def get_pending_by_idempotency_key(
        self,
        *,
        idempotency_key: str,
    ) -> BookingGroup | None:
        return (
            self.db.query(BookingGroup)
            .filter(
                BookingGroup.idempotency_key == idempotency_key,
                ~self.db.query(Booking)
                .filter(
                    Booking.booking_group_id == BookingGroup.id,
                    Booking.booking_status != "PENDING",
                )
                .exists(),
            )
            .first()
        )