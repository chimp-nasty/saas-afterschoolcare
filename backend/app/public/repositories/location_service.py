from uuid import UUID
from datetime import date

from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.public.models.location_service import LocationService
from app.public.models.location_service_day import LocationServiceDay
from app.public.models.service_type import ServiceType


class LocationServiceRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        service_type_id: int,
        stripe_product_id: str | None = None,
        stripe_price_id: str | None = None,
        is_active: bool = True,
    ) -> LocationService:
        record = LocationService(
            location_id=location_id,
            service_type_id=service_type_id,
            stripe_product_id=stripe_product_id,
            stripe_price_id=stripe_price_id,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> LocationService | None:
        return (
            self.db.query(LocationService)
            .filter(LocationService.id == id)
            .first()
        )

    def list_by_service_day_ids(
        self,
        *,
        ids: list[UUID],
    ):
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