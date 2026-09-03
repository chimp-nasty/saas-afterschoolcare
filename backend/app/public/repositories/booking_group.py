from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.booking_group import BookingGroup


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
