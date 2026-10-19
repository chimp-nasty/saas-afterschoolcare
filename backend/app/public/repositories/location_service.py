from uuid import UUID

from sqlalchemy import Date, Row, cast, func

from app.db.repository import Repository
from app.db.models import Location, LocationService, ServiceType


class LocationServiceRepository(Repository):
    def create(
        self,
        *,
        location_id: UUID,
        service_type_id: int,
        current_price_cents: int,
        currency: str,
        stripe_product_id: str | None = None,
        is_active: bool = True,
    ) -> LocationService:
        record = LocationService(
            location_id=location_id,
            service_type_id=service_type_id,
            current_price_cents=current_price_cents,
            currency=currency,
            stripe_product_id=stripe_product_id,
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

    def get_child_age_limits(
        self,
        *,
        location_id: UUID,
    ) -> Row | None:
        """
        The widest age range the location's active services accept, and
        today's date there: (min_age, max_age, today). min_age and max_age
        are None when the location has no active services.
        """
        return (
            self.db.query(
                func.min(LocationService.min_child_age).label("min_age"),
                func.max(LocationService.max_child_age).label("max_age"),
                cast(func.timezone(Location.timezone, func.now()), Date).label("today"),
            )
            .select_from(Location)
            .outerjoin(
                LocationService,
                (LocationService.location_id == Location.id)
                & LocationService.is_active,
            )
            .filter(Location.id == location_id)
            .group_by(Location.timezone)
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

        return self._all(
            query.order_by(ServiceType.name.asc())
        )