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
        location_service_repository: LocationServiceDayRepository,
    ):
        self.db = db

        self.location_service_repository = (
            location_service_repository
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
            LocationServiceDayTableResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]