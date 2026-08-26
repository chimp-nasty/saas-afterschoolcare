from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.booking_status_history import BookingStatusHistory


class BookingStatusHistoryRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        booking_id: UUID,
        new_status_id: int,
        old_status_id: int | None = None,
        changed_by_user_id: UUID | None = None,
        note: str | None = None,
    ) -> BookingStatusHistory:
        record = BookingStatusHistory(
            booking_id=booking_id,
            new_status_id=new_status_id,
            old_status_id=old_status_id,
            changed_by_user_id=changed_by_user_id,
            note=note,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> BookingStatusHistory | None:
        return (
            self.db.query(BookingStatusHistory)
            .filter(BookingStatusHistory.id == id)
            .first()
        )
