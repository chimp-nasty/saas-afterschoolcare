from uuid import UUID
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy.engine import Row

from app.public.models.location_service import LocationService
from app.public.models.location_service_day import LocationServiceDay
from app.public.models.service_type import ServiceType


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

    def list_by_service_day_ids(
        self,
        *,
        ids: list[UUID],
    ) -> list[Row]:
        return (
            self.db.query(
                LocationServiceDay.id.label(
                    "location_service_day_id"
                ),
                LocationServiceDay.service_date,
                LocationServiceDay.capacity,

                LocationService.id.label(
                    "location_service_id"
                ),

                LocationService.current_price_cents,
                LocationService.currency,

                LocationService.stripe_product_id,
                LocationService.stripe_price_id,
            )
            .join(
                LocationService,
                LocationService.id
                == LocationServiceDay.location_service_id,
            )
            .filter(
                LocationServiceDay.id.in_(ids),
            )
            .order_by(
                LocationServiceDay.id,
            )
            .with_for_update()
            .all()
        )

    def list_context_with_filters(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        is_open: bool | None = None,
    ) -> list[Row]:
        query = (
            self.db.query(
                LocationServiceDay.id,
                LocationServiceDay.location_service_id,
                LocationService.service_type_id,

                ServiceType.name.label("service_name"),

                LocationService.current_price_cents,
                LocationService.currency,

                LocationServiceDay.service_date,
                LocationServiceDay.is_open,
                LocationServiceDay.capacity,
            )
            .join(
                LocationService,
                LocationService.id
                == LocationServiceDay.location_service_id,
            )
            .join(
                ServiceType,
                ServiceType.id
                == LocationService.service_type_id,
            )
        )

        if date_from:
            query = query.filter(
                LocationServiceDay.service_date >= date_from
            )

        if date_to:
            query = query.filter(
                LocationServiceDay.service_date <= date_to
            )

        if is_open is not None:
            query = query.filter(
                LocationServiceDay.is_open == is_open
            )

        return (
            query
            .order_by(
                LocationServiceDay.service_date.asc()
            )
            .all()
        )