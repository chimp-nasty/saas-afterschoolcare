from uuid import UUID
from sqlalchemy.orm import Session

from app.errors.tenancy import LocationNotFoundError
from app.tenancy.schemas.location_branding import PublicLocationResponse
from app.tenancy.repositories.location_branding import LocationBrandingRepository


class LocationBrandingService:
    def __init__(self, *, db: Session):
        self.db = db
        self.repo = LocationBrandingRepository(db=db)

    def get_public_location(
        self,
        *,
        location_id: UUID
    ) -> PublicLocationResponse:
        result = self.repo.get_location_with_branding_by_id(
            location_id=location_id
        )

        if result is None:
            raise LocationNotFoundError()

        location, tenant, branding = result

        return PublicLocationResponse(
            tenant_name=tenant.name,
            tenant_code=tenant.code,

            location_code=location.code,
            location_name=location.name,

            display_name=branding.display_name if branding else None,
            logo_key=branding.logo_key if branding else None,
            primary_color=branding.primary_color if branding else None,
            secondary_color=branding.secondary_color if branding else None,
            font_family=branding.font_family if branding else None,
        )