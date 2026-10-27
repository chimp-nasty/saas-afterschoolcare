from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission, resolve_location_id
from app.dependencies.db import get_db
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.errors.tenancy import SiteFileNotFoundError
from app.public.services.location_service import LocationServiceService
from app.public.schemas.location_service import (
    FeaturedServiceResponse,
    LocationServiceSelectionResponse,
    LocationServiceSettingsResponse,
    UpdateLocationServiceConfigRequest,
)
from app.tenancy.schemas.site import ConfirmPhotoUploadRequest, SiteUploadResponse, StartPhotoUploadRequest


router = APIRouter(
    prefix="/location-services/v1",
    tags=["location-services"],
)


@router.get("/public/{location_code}")
def list_public_location_services(
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: LocationServiceService = Depends(
        get_service(
            LocationServiceService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[list[LocationServiceSelectionResponse]]:
    # The landing page, before login: services and config are public.
    result = service.list_offered(
        location_id=location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched services",
        data=result,
    )


# The centre page's leading service and its next session (docs/public-site.md).
# Public, like the services list.
@router.get("/public/{location_code}/featured")
def get_featured_location_service(
    location_id: UUID = Depends(resolve_location_id),
    service: LocationServiceService = Depends(get_service(LocationServiceService, db_dependency=get_db)),
) -> ApiResponse[FeaturedServiceResponse | None]:
    return ApiResponse(ok=True, msg="Fetched the featured service", data=service.featured(location_id=location_id))


# Every service the location has, offered or not, for the superadmin's settings
# (location_services u: only superadmins change them, so only they need this).
@router.get("/settings")
def list_location_service_settings(
    ctx: TokenContext = Depends(require_permission(resource="location_services", action="u")),
    service: LocationServiceService = Depends(get_service(LocationServiceService, db_dependency=get_rls_db)),
) -> ApiResponse[list[LocationServiceSettingsResponse]]:
    return ApiResponse(ok=True, msg="Fetched service settings", data=service.list_settings(location_id=ctx.location_id))


@router.patch("/{location_service_id}/config")
def update_location_service_config(
    location_service_id: UUID,
    body: UpdateLocationServiceConfigRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_services",
            action="u",
        )
    ),
    service: LocationServiceService = Depends(
        get_service(
            LocationServiceService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[LocationServiceSettingsResponse]:
    result = service.update_config(
        location_service_id=location_service_id,
        location_id=ctx.location_id,
        user_id=ctx.user_id,
        body=body,
    )

    return ApiResponse(
        ok=True,
        msg="Service updated",
        data=result,
    )


@router.get("/")
def list_location_services(
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_services",
            action="r",
        )
    ),
    service: LocationServiceService = Depends(
        get_service(
            LocationServiceService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[LocationServiceSelectionResponse]]:
    result = service.list_offered(
        location_id=ctx.location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched services",
        data=result
    )


# A program's photo (docs/public-site.md, stage 9b), set inline on the
# programs page by a superadmin there (location_services u): a signed upload
# straight to storage, then confirm it; taking it off. Its description is
# saved with the rest of the config (PATCH .../config, photo_alt).
@router.post("/{location_service_id}/photo/uploads")
def start_program_photo_upload(
    location_service_id: UUID,
    body: StartPhotoUploadRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_services", action="u")),
    service: LocationServiceService = Depends(get_service(LocationServiceService, db_dependency=get_rls_db)),
) -> ApiResponse[SiteUploadResponse]:
    return ApiResponse(
        ok=True,
        msg="Upload started",
        data=service.start_photo_upload(
            location_service_id=location_service_id,
            location_id=ctx.location_id,
            content_type=body.content_type,
        ),
    )


@router.post("/{location_service_id}/photo/uploads/confirm")
def confirm_program_photo_upload(
    location_service_id: UUID,
    body: ConfirmPhotoUploadRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_services", action="u")),
    service: LocationServiceService = Depends(get_service(LocationServiceService, db_dependency=get_rls_db)),
) -> ApiResponse[LocationServiceSettingsResponse]:
    return ApiResponse(
        ok=True,
        msg="Photo saved",
        data=service.confirm_photo_upload(
            location_service_id=location_service_id,
            location_id=ctx.location_id,
            user_id=ctx.user_id,
            key=body.key,
        ),
    )


@router.delete("/{location_service_id}/photo")
def remove_program_photo(
    location_service_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="location_services", action="u")),
    service: LocationServiceService = Depends(get_service(LocationServiceService, db_dependency=get_rls_db)),
) -> ApiResponse[LocationServiceSettingsResponse]:
    return ApiResponse(
        ok=True,
        msg="Photo removed",
        data=service.remove_photo(
            location_service_id=location_service_id,
            location_id=ctx.location_id,
            user_id=ctx.user_id,
        ),
    )


# The program's photo on the public programs page: a redirect to a
# short-lived link (its link carries the photo's version, ?v=). Public.
@router.get("/public/{location_code}/{location_service_id}/photo")
def get_program_photo(
    location_service_id: UUID,
    location_id: UUID = Depends(resolve_location_id),
    service: LocationServiceService = Depends(get_service(LocationServiceService, db_dependency=get_db)),
) -> RedirectResponse:
    url = service.photo_url(location_service_id=location_service_id, location_id=location_id)

    if url is None:
        raise SiteFileNotFoundError()

    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, max-age=600"})
