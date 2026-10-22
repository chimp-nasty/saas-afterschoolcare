from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors.tenancy import LocationNotFoundError
from app.tenancy.schemas.location_branding import PublicLocationResponse
from app.tenancy.repositories.location_branding import LocationBrandingRepository


def _to_public_location(location, tenant, branding) -> PublicLocationResponse:
    return PublicLocationResponse(
        tenant_name=tenant.name,
        tenant_code=tenant.code,

        location_id=location.id,
        location_code=location.code,
        # locations.name is optional; families always need something to
        # call it, so fall back to its code.
        location_name=location.name or location.code,

        address_line_1=location.address_line_1,
        address_line_2=location.address_line_2,
        suburb=location.suburb,
        state=location.state,
        postcode=location.postcode,

        latitude=float(location.latitude) if location.latitude is not None else None,
        longitude=float(location.longitude) if location.longitude is not None else None,
        google_place_id=location.google_place_id,

        phone=location.phone,
        email=location.email,

        display_name=branding.display_name if branding else None,
        logo_key=branding.logo_key if branding else None,
        primary_color=branding.primary_color if branding else None,
        secondary_color=branding.secondary_color if branding else None,
        font_family=branding.font_family if branding else None,
    )


class LocationBrandingService:
    def __init__(
        self,
        *,
        db: Session,
        location_branding_repo: LocationBrandingRepository,
    ):
        self.db = db
        self.location_branding_repo = location_branding_repo

    def get_public_location(
        self,
        *,
        location_id: UUID
    ) -> PublicLocationResponse:
        result = (
            self.location_branding_repo.get_location_with_branding_by_id(
                location_id=location_id
            )
        )

        if result is None:
            raise LocationNotFoundError()

        return _to_public_location(*result)

    def list_public_locations(
        self,
        *,
        tenant_id: UUID,
    ) -> list[PublicLocationResponse]:
        return [
            _to_public_location(*row)
            for row in self.location_branding_repo.list_locations_with_branding_by_tenant_id(
                tenant_id=tenant_id,
            )
        ]


    def bookings_open(
        self,
        *,
        location_id: UUID,
    ) -> bool:
        """
        Whether families can book and pay here now: the business's Stripe
        account can take payments (tenancy.payments_account, schema/0002).
        """
        return self.db.execute(
            select(func.tenancy.payments_account(location_id))
        ).scalar() is not None
