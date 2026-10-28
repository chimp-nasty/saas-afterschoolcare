from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.platform import (
    PlatformContext,
    get_platform_context,
    get_platform_db,
    require_platform_site,
)
from app.dependencies.service import get_service
from app.errors.tenancy import SiteFileNotFoundError
from app.platform.schemas.site import (
    ConfirmPlatformUploadRequest,
    PlatformFeaturesRequest,
    PlatformFileKind,
    PlatformSiteRequest,
    PlatformSiteResponse,
    StartPlatformUploadRequest,
)
from app.platform.services.platform_site import PlatformSiteService
from app.tenancy.schemas.site import SiteUploadResponse


# The platform's landing page and branding (docs/platform-site.md), on the
# platform's own site only.
#   GET / and GET /files/{kind}: anyone (the page and its header).
#   The rest: the platform's admins (their own login, get_platform_context;
#     the platform has no tenant permissions), editing in place on the page.
router = APIRouter(
    prefix="/platform-site/v1",
    tags=["platform"],
    dependencies=[Depends(require_platform_site)],
)

_public = get_service(PlatformSiteService, db_dependency=get_db)
_service = get_service(PlatformSiteService, db_dependency=get_platform_db)

_REMOVED = {"logo": "Logo removed", "icon": "Site icon removed", "hero_photo": "Photo removed", "about_photo": "Photo removed"}


@router.get("/")
def get_platform_site(
    service: PlatformSiteService = Depends(_public),
) -> ApiResponse[PlatformSiteResponse]:
    return ApiResponse(ok=True, msg="Fetched the platform's site", data=service.get())


# The logo, site icon (its logo if it has none) or a photo: a redirect to a
# short-lived link to the file. With no icon or logo, the app's own icon.
@router.get("/files/{kind}")
def get_platform_file(
    kind: PlatformFileKind,
    service: PlatformSiteService = Depends(_public),
) -> RedirectResponse:
    url = service.public_file_url(kind=kind)

    if url is None and kind == "icon":
        url = "/favicon.svg"

    if url is None:
        raise SiteFileNotFoundError()

    # Browsers may reuse the redirect for a while, well inside the link's life.
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, max-age=600"})


@router.put("/")
def update_platform_site(
    body: PlatformSiteRequest,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformSiteService = Depends(_service),
) -> ApiResponse[PlatformSiteResponse]:
    return ApiResponse(ok=True, msg="Site saved", data=service.update(body=body))


@router.put("/features")
def replace_platform_features(
    body: PlatformFeaturesRequest,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformSiteService = Depends(_service),
) -> ApiResponse[PlatformSiteResponse]:
    return ApiResponse(ok=True, msg="Features saved", data=service.replace_features(features=body.features))


# A signed upload straight to storage, then confirm it.
@router.post("/uploads")
def start_platform_upload(
    body: StartPlatformUploadRequest,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformSiteService = Depends(_service),
) -> ApiResponse[SiteUploadResponse]:
    return ApiResponse(
        ok=True,
        msg="Upload started",
        data=service.start_upload(kind=body.kind, content_type=body.content_type),
    )


@router.post("/uploads/confirm")
def confirm_platform_upload(
    body: ConfirmPlatformUploadRequest,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformSiteService = Depends(_service),
) -> ApiResponse[PlatformSiteResponse]:
    return ApiResponse(ok=True, msg="File saved", data=service.confirm_upload(kind=body.kind, key=body.key))


@router.delete("/files/{kind}")
def remove_platform_file(
    kind: PlatformFileKind,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformSiteService = Depends(_service),
) -> ApiResponse[PlatformSiteResponse]:
    return ApiResponse(ok=True, msg=_REMOVED[kind], data=service.remove_image(kind=kind))
