from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.location_service_day import LocationServiceDay


class LocationServiceDayRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_service_id: UUID,
        service_date,
        capacity: int,
        is_open: bool = True,
    ) -> LocationServiceDay:
        record = LocationServiceDay(
            location_service_id=location_service_id,
            service_date=service_date,
            capacity=capacity,
            is_open=is_open,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> LocationServiceDay | None:
        return (
            self.db.query(LocationServiceDay)
            .filter(LocationServiceDay.id == id)
            .first()
        )
