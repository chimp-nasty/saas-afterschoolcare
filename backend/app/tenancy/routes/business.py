from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_tenant_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.tenancy.schemas.business import (
    BusinessLocationRequest,
    BusinessLocationResponse,
    BusinessOverviewResponse,
    BusinessSettingsRequest,
    BusinessSettingsResponse,
)
from app.tenancy.schemas.site import (
    ConfirmSiteUploadRequest,
    FaqsRequest,
    SiteRequest,
    SiteResponse,
    SiteUploadResponse,
    StartSiteUploadRequest,
)
from app.tenancy.services.business import BusinessService
from app.tenancy.services.site import SiteService


# Business settings (/business): the whole business, run by the tenant's
# owner whichever location they're logged in at, or none
# (docs/tenant-administration.md). Tenant permissions only: tenant_settings
# for its details and its site (Your site), tenant_locations for its
# locations. Stripe is in stripe_account.py.
router = APIRouter(
    prefix="/business/v1",
    tags=["business"],
)

_service = get_service(BusinessService, db_dependency=get_rls_db)
_site_service = get_service(SiteService, db_dependency=get_rls_db)


@router.get("/overview")
def get_overview(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="r")),
    service: BusinessService = Depends(_service),
) -> ApiResponse[BusinessOverviewResponse]:
    return ApiResponse(ok=True, msg="Fetched business overview", data=service.overview(tenant_id=ctx.tenant_id))


@router.get("/settings")
def get_settings(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="r")),
    service: BusinessService = Depends(_service),
) -> ApiResponse[BusinessSettingsResponse]:
    return ApiResponse(ok=True, msg="Fetched business details", data=service.get_settings(tenant_id=ctx.tenant_id))


@router.put("/settings")
def update_settings(
    body: BusinessSettingsRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="u")),
    service: BusinessService = Depends(_service),
) -> ApiResponse[BusinessSettingsResponse]:
    return ApiResponse(
        ok=True,
        msg="Business details saved",
        data=service.update_settings(tenant_id=ctx.tenant_id, body=body),
    )


@router.get("/locations")
def list_locations(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_locations", action="r")),
    service: BusinessService = Depends(_service),
) -> ApiResponse[list[BusinessLocationResponse]]:
    return ApiResponse(ok=True, msg="Fetched centres", data=service.list_locations(tenant_id=ctx.tenant_id))


@router.post("/locations", status_code=201)
def create_location(
    body: BusinessLocationRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_locations", action="c")),
    service: BusinessService = Depends(_service),
) -> ApiResponse[BusinessLocationResponse]:
    return ApiResponse(
        ok=True,
        msg="Centre added",
        data=service.create_location(tenant_id=ctx.tenant_id, body=body),
    )


@router.put("/locations/{location_id}")
def update_location(
    location_id: UUID,
    body: BusinessLocationRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_locations", action="u")),
    service: BusinessService = Depends(_service),
) -> ApiResponse[BusinessLocationResponse]:
    return ApiResponse(
        ok=True,
        msg="Centre saved",
        data=service.update_location(tenant_id=ctx.tenant_id, location_id=location_id, body=body),
    )


# ---------------------------------------------------------------------------
# Your site (stage 5): the landing page's headline, colours, logo and icon,
# FAQs and policy PDFs.
# ---------------------------------------------------------------------------


@router.get("/site")
def get_site(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="r")),
    service: SiteService = Depends(_site_service),
) -> ApiResponse[SiteResponse]:
    return ApiResponse(ok=True, msg="Fetched your site", data=service.get_site(tenant_id=ctx.tenant_id))


@router.put("/site")
def update_site(
    body: SiteRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="u")),
    service: SiteService = Depends(_site_service),
) -> ApiResponse[SiteResponse]:
    return ApiResponse(ok=True, msg="Your site saved", data=service.update_site(tenant_id=ctx.tenant_id, body=body))


@router.put("/site/faqs")
def replace_faqs(
    body: FaqsRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="u")),
    service: SiteService = Depends(_site_service),
) -> ApiResponse[SiteResponse]:
    return ApiResponse(ok=True, msg="Questions saved", data=service.replace_faqs(tenant_id=ctx.tenant_id, faqs=body.faqs))


# A signed upload straight to storage, then confirm it.
@router.post("/site/uploads")
def start_site_upload(
    body: StartSiteUploadRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="u")),
    service: SiteService = Depends(_site_service),
) -> ApiResponse[SiteUploadResponse]:
    return ApiResponse(
        ok=True,
        msg="Upload started",
        data=service.start_upload(tenant_id=ctx.tenant_id, kind=body.kind, content_type=body.content_type),
    )


@router.post("/site/uploads/confirm")
def confirm_site_upload(
    body: ConfirmSiteUploadRequest,
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="u")),
    service: SiteService = Depends(_site_service),
) -> ApiResponse[SiteResponse]:
    return ApiResponse(
        ok=True,
        msg="File saved",
        data=service.confirm_upload(tenant_id=ctx.tenant_id, user_id=ctx.user_id, kind=body.kind, key=body.key),
    )


@router.delete("/site/{kind}")
def remove_site_image(
    kind: Literal["logo", "icon"],
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_settings", action="u")),
    service: SiteService = Depends(_site_service),
) -> ApiResponse[SiteResponse]:
    return ApiResponse(
        ok=True,
        msg="Logo removed" if kind == "logo" else "Site icon removed",
        data=service.remove_image(tenant_id=ctx.tenant_id, kind=kind),
    )
