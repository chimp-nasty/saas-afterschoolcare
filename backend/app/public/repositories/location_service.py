from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.location_service import LocationService


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
