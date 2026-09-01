from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.engine import Row

from app.tenancy.models.location_branding import LocationBranding
from app.tenancy.models.location import Location
from app.tenancy.models.tenant import Tenant


class LocationBrandingRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        display_name: str | None = None,
        logo_key: str | None = None,
        primary_color: str | None = None,
        secondary_color: str | None = None,
        font_family: str | None = None,
    ) -> LocationBranding:
        record = LocationBranding(
            location_id=location_id,
            display_name=display_name,
            logo_key=logo_key,
            primary_color=primary_color,
            secondary_color=secondary_color,
            font_family=font_family,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> LocationBranding | None:
        return (
            self.db.query(LocationBranding)
            .filter(LocationBranding.id == id)
            .first()
        )

    def get_location_with_branding_by_id(
        self,
        *,
        location_id: UUID,
    ):
        stmt = (
            select(
                Location,
                Tenant,
                LocationBranding,
            )
            .join(
                Tenant,
                Tenant.id == Location.tenant_id,
            )
            .outerjoin(
                LocationBranding,
                LocationBranding.location_id == Location.id,
            )
            .where(
                Location.id == location_id,
                Location.is_active.is_(True),
            )
        )

        return self.db.execute(stmt).first()