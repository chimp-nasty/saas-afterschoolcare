from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.platform import require_platform_site
from app.dependencies.service import get_service
from app.platform.schemas.platform import (
    InviteDetailsResponse,
    RegisterTenantRequest,
    RegisteredTenantResponse,
)
from app.platform.services.registration import RegistrationService


# A business registering with its invite, on the platform's site. No login:
# the invite is the permission (docs/tenant-administration.md, stage 4).
router = APIRouter(
    prefix="/registration/v1",
    tags=["registration"],
    dependencies=[Depends(require_platform_site)],
)

_service = get_service(RegistrationService, db_dependency=get_db)


@router.get("/invites/{token}")
def get_invite(
    token: str,
    service: RegistrationService = Depends(_service),
) -> ApiResponse[InviteDetailsResponse]:
    return ApiResponse(ok=True, msg="Fetched invite", data=service.invite_details(token=token))


@router.post("/register", status_code=201)
def register(
    body: RegisterTenantRequest,
    service: RegistrationService = Depends(_service),
) -> ApiResponse[RegisteredTenantResponse]:
    return ApiResponse(ok=True, msg="Your business is set up", data=service.register(body=body))
