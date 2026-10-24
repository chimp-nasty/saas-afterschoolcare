from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.response import ApiResponse
from app.auth.schemas.auth import LoginRequest
from app.core.config import settings
from app.dependencies.auth import site_origin
from app.dependencies.db import get_db
from app.dependencies.platform import (
    PLATFORM_COOKIE_NAME,
    PlatformContext,
    get_platform_context,
    get_platform_db,
    require_platform_site,
)
from app.dependencies.service import get_service
from app.platform.schemas.platform import (
    CreateInviteRequest,
    CreatedInviteResponse,
    InviteResponse,
    PlatformSessionResponse,
    PlatformTenantResponse,
    SetTenantActiveRequest,
)
from app.platform.services.platform import PlatformService


# The platform's site (docs/tenant-administration.md, stage 4): its admins,
# on the bare base domain only. Their own login and cookie, never a
# tenant's; every endpoint after login needs it (get_platform_context).
router = APIRouter(
    prefix="/platform/v1",
    tags=["platform"],
    dependencies=[Depends(require_platform_site)],
)

_service = get_service(PlatformService, db_dependency=get_platform_db)


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    service: PlatformService = Depends(get_service(PlatformService, db_dependency=get_db)),
) -> ApiResponse[None]:
    response.set_cookie(
        key=PLATFORM_COOKIE_NAME,
        value=service.login(body=body),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return ApiResponse(ok=True, msg="Login successful", data=None)


@router.post("/logout")
def logout(
    response: Response,
) -> ApiResponse[None]:
    response.delete_cookie(
        key=PLATFORM_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

    return ApiResponse(ok=True, msg="Logged out", data=None)


@router.get("/session")
def get_session(
    ctx: PlatformContext = Depends(get_platform_context),
    service: PlatformService = Depends(_service),
) -> ApiResponse[PlatformSessionResponse]:
    return ApiResponse(ok=True, msg="Session retrieved", data=service.session(ctx=ctx))


@router.get("/tenants")
def list_tenants(
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformService = Depends(_service),
) -> ApiResponse[list[PlatformTenantResponse]]:
    return ApiResponse(ok=True, msg="Fetched businesses", data=service.list_tenants())


@router.put("/tenants/{tenant_id}/active")
def set_tenant_active(
    tenant_id: UUID,
    body: SetTenantActiveRequest,
    ctx: PlatformContext = Depends(get_platform_context),
    service: PlatformService = Depends(_service),
) -> ApiResponse[None]:
    service.set_tenant_active(tenant_id=tenant_id, is_active=body.is_active, ctx=ctx)

    return ApiResponse(
        ok=True,
        msg="Business switched on" if body.is_active else "Business switched off",
        data=None,
    )


@router.get("/invites")
def list_invites(
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformService = Depends(_service),
) -> ApiResponse[list[InviteResponse]]:
    return ApiResponse(ok=True, msg="Fetched invites", data=service.list_invites())


@router.post("/invites", status_code=201)
def create_invite(
    body: CreateInviteRequest,
    origin: str = Depends(site_origin),
    ctx: PlatformContext = Depends(get_platform_context),
    service: PlatformService = Depends(_service),
) -> ApiResponse[CreatedInviteResponse]:
    return ApiResponse(
        ok=True,
        msg="Invite created",
        data=service.create_invite(email=str(body.email), origin=origin, ctx=ctx),
    )


@router.delete("/invites/{invite_id}")
def revoke_invite(
    invite_id: UUID,
    ctx: PlatformContext = Depends(get_platform_context),
    service: PlatformService = Depends(_service),
) -> ApiResponse[None]:
    service.revoke_invite(invite_id=invite_id, ctx=ctx)

    return ApiResponse(ok=True, msg="Invite revoked", data=None)
