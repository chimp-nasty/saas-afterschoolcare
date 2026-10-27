from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.response import ApiResponse
from app.dependencies.auth import resolve_location_id, resolve_tenant_id
from app.dependencies.db import get_db
from app.dependencies.service import get_service
from app.core.cache.cache import cached
from app.core.cache.stores import cache_stores

from app.errors.tenancy import SiteFileNotFoundError
from app.tenancy.services.location_branding import LocationBrandingService
from app.tenancy.services.site import SiteService
from app.tenancy.schemas.location_branding import PublicLocationResponse
from app.tenancy.schemas.site import PublicBusinessResponse, SiteFileKind


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


# The business's landing page ("/", stage 5): its words, colours, FAQs and
# which images and policies it has. Public.
@router.get("/public/business")
def get_public_business(
    tenant_id: UUID = Depends(
        resolve_tenant_id,
    ),
    service: SiteService = Depends(
        get_service(
            SiteService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[PublicBusinessResponse]:
    return ApiResponse(
        ok=True,
        msg="Fetched business",
        data=service.public_business(tenant_id=tenant_id),
    )


# The business's logo, site icon (its logo if it has none), photo or current
# policy PDF: a redirect to a short-lived link to the file. Public. With no
# icon or logo at all, the platform's own icon. A photo's link carries its
# version (?v=), so a new one isn't hidden by a cached redirect.
# Not under /public/ (a centre's code goes there).
@router.get("/site-files/{kind}")
def get_public_file(
    kind: SiteFileKind,
    tenant_id: UUID = Depends(
        resolve_tenant_id,
    ),
    service: SiteService = Depends(
        get_service(
            SiteService,
            db_dependency=get_db,
        )
    ),
) -> RedirectResponse:
    url = service.public_file_url(tenant_id=tenant_id, kind=kind)

    if url is None and kind == "icon":
        url = "/favicon.svg"

    if url is None:
        raise SiteFileNotFoundError()

    # Browsers may reuse the redirect for a while, well inside the link's life.
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, max-age=600"})


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
