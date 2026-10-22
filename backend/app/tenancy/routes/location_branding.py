from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.dependencies.auth import resolve_location_id, resolve_tenant_id
from app.dependencies.db import get_db
from app.dependencies.service import get_service
from app.core.cache.cache import cached
from app.core.cache.stores import cache_stores

from app.tenancy.services.location_branding import LocationBrandingService
from app.tenancy.schemas.location_branding import PublicLocationResponse


router = APIRouter(
    prefix="/location-branding/v1",
    tags=["location-branding"],
)


@router.get("/public")
def list_public_locations(
    tenant_id: UUID = Depends(
        resolve_tenant_id,
    ),
    service: LocationBrandingService = Depends(
        get_service(
            LocationBrandingService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[list[PublicLocationResponse]]:
    # The tenant's landing page ("/"), before login: its centres to choose from.
    result = service.list_public_locations(
        tenant_id=tenant_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched public locations",
        data=result,
    )


@router.get("/public/{location_code}")
@cached(
    cache=cache_stores.location_branding,
    key_by="location_id",
)
def get_public_branding(
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: LocationBrandingService = Depends(
        get_service(
            LocationBrandingService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[PublicLocationResponse]:
    result = service.get_public_location(
        location_id=location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched public location data",
        data=result,
    )



# Whether families can book and pay at this location now (its business's
# Stripe account can take payments). Not cached: it changes when the
# business connects Stripe or turns payments off.
@router.get("/public/{location_code}/bookings-open")
def get_bookings_open(
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: LocationBrandingService = Depends(
        get_service(
            LocationBrandingService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[bool]:
    return ApiResponse(
        ok=True,
        msg="Fetched whether bookings are open",
        data=service.bookings_open(location_id=location_id),
    )
