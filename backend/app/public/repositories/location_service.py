from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import Row

from app.public.models.location_service import LocationService
from app.public.models.service_type import ServiceType


class LocationServiceRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        service_type_id: int,
        current_price_cents: int,
        currency: str,
        stripe_product_id: str | None = None,
        stripe_price_id: str | None = None,
        is_active: bool = True,
    ) -> LocationService:
        record = LocationService(
            location_id=location_id,
            service_type_id=service_type_id,
            current_price_cents=current_price_cents,
            currency=currency,
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

    def get_by_stripe_product_id(
        self,
        *,
        stripe_product_id: str
    ) -> LocationService | None:
        return (
            self.db.query(LocationService)
            .filter(LocationService.stripe_product_id == stripe_product_id)
            .first()
        )

    def update_current_price_cents(
        self,
        *,
        location_service: LocationService,
        amount_cents: int,
        currency: str
    ) -> None:
        location_service.current_price_cents = amount_cents
        location_service.currency = currency

    def list_with_context(
        self,
        *,
        is_active: bool | None = None,
    ) -> list[Row]:
        query = (
            self.db.query(
                LocationService.id,
                LocationService.service_type_id,

                ServiceType.name.label("service_name"),

                LocationService.current_price_cents,
                LocationService.currency,
            )
            .join(
                ServiceType,
                ServiceType.id
                == LocationService.service_type_id,
            )
        )

        if is_active is not None:
            query = query.filter(
                LocationService.is_active == is_active
            )

        return (
            query
            .order_by(ServiceType.name.asc())
            .all()
        )