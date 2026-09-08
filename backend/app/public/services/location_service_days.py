from sqlalchemy.orm import Session

from app.public.repositories.location_service_day import LocationServiceDayRepository
from app.public.schemas.location_service_days import (
    ListLocationServiceDaysFilterRequest,
    LocationServiceDayTableResponse,
)


class LocationServiceDayService:
    def __init__(
        self,
        *,
        db: Session,
    ):
        self.db = db

        self.location_service_repository = (
            LocationServiceDayRepository(db=db)
        )

    def list_with_filters(
        self,
        *,
        filters: ListLocationServiceDaysFilterRequest,
    ) -> list[LocationServiceDayTableResponse]:
        rows = (
            self.location_service_repository
            .list_context_with_filters(
                date_from=filters.date_from,
                date_to=filters.date_to,
                is_open=filters.is_open,
            )
        )

        return [
            LocationServiceDayTableResponse(
                id=row.id,
                location_service_id=row.location_service_id,
                service_type_id=row.service_type_id,
                service_name=row.service_name,
                service_date=row.service_date,
                is_open=row.is_open,
                capacity=row.capacity,
            )
            for row in rows
        ]