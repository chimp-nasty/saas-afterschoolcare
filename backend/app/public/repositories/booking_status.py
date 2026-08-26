from sqlalchemy.orm import Session

from app.public.models.booking_status import BookingStatus


class BookingStatusRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        code: str,
        label: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> BookingStatus:
        record = BookingStatus(
            code=code,
            label=label,
            description=description,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: int,
    ) -> BookingStatus | None:
        return (
            self.db.query(BookingStatus)
            .filter(BookingStatus.id == id)
            .first()
        )
