from uuid import UUID

from sqlalchemy import select

from app.db.repository import Repository
from app.db.models import (
    Location,
    Tenant,
    TenantBranding,
)


class LocationBrandingRepository(Repository):
    """
    Locations as the public pages show them, with their business's
    branding (one brand per business: tenancy.tenant_branding).
    """

    def list_locations_with_branding_by_tenant_id(
        self,
        *,
        tenant_id: UUID,
    ):
        """The tenant's active locations, with branding, by name."""
        stmt = (
            select(
                Location,
                Tenant,
                TenantBranding,
            )
            .join(
                Tenant,
                Tenant.id == Location.tenant_id,
            )
            .outerjoin(
                TenantBranding,
                TenantBranding.tenant_id == Location.tenant_id,
            )
            .where(
                Location.tenant_id == tenant_id,
                Location.is_active.is_(True),
            )
            .order_by(Location.name.asc(), Location.code.asc())
        )

        return self.db.execute(stmt).all()

    def get_location_with_branding_by_id(
        self,
        *,
        location_id: UUID,
    ):
        stmt = (
            select(
                Location,
                Tenant,
                TenantBranding,
            )
            .join(
                Tenant,
                Tenant.id == Location.tenant_id,
            )
            .outerjoin(
                TenantBranding,
                TenantBranding.tenant_id == Location.tenant_id,
            )
            .where(
                Location.id == location_id,
                Location.is_active.is_(True),
            )
        )

        return self.db.execute(stmt).first()
