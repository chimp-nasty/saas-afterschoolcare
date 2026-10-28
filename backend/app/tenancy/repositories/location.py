from typing import Any
from uuid import UUID

from sqlalchemy import func

from app.db.repository import Repository
from app.db.models import Location, LocationServiceConfig


class LocationRepository(Repository):
    def create(
        self,
        *,
        tenant_id: UUID,
        name: str | None = None,
        code: str,
        address_line_1: str,
        address_line_2: str | None = None,
        suburb: str,
        state: str,
        postcode: str,
        phone: str | None = None,
        email: str | None = None,
        timezone: str = "Australia/Brisbane",
        enquiry_notice_email: str | None = None,
        is_active: bool = True,
    ) -> Location:
        record = Location(
            tenant_id=tenant_id,
            name=name,
            code=code,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            suburb=suburb,
            state=state,
            postcode=postcode,
            phone=phone,
            email=email,
            timezone=timezone,
            enquiry_notice_email=enquiry_notice_email,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Location | None:
        return (
            self.db.query(Location)
            .filter(Location.id == id)
            .first()
        )

    def get_by_tenant_and_code(
        self,
        *,
        tenant_id: UUID,
        code: str
    ) -> Location:
        return (
            self.db.query(Location)
            .filter(
                Location.tenant_id == tenant_id,
                Location.code == code,
            )
            .first()
        )

    def list_for_tenant_with_services_offered(
        self,
        *,
        tenant_id: UUID,
    ) -> list[tuple[Location, int]]:
        """Every location of the tenant, by name, with how many services it offers."""
        offered = func.count(LocationServiceConfig.location_service_id).filter(
            LocationServiceConfig.is_active,
        )

        return (
            self.db.query(Location, offered)
            .outerjoin(
                LocationServiceConfig,
                LocationServiceConfig.location_id == Location.id,
            )
            .filter(Location.tenant_id == tenant_id)
            .group_by(Location.id)
            .order_by(Location.name)
            .all()
        )

    def update(
        self,
        *,
        location: Location,
        values: dict[str, Any],
    ) -> Location:
        for field, value in values.items():
            setattr(location, field, value)

        self.db.flush()

        return location
