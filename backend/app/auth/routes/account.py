from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.auth.schemas.account import AccountResponse, ChangePasswordRequest, DeactivateAccountRequest
from app.auth.services.account import AccountService
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service


# Your own account (own_account, every role on the web): r to read your
# details and where you work, u to change your password. Changing it needs
# the current password and is rate limited (app/middleware/__init__.py).
# Families also deactivate their account here (u, with their password,
# rate limited too) and ask to be reactivated (u); reading the account and
# asking still work while deactivated (docs/account-deactivation.md).
router = APIRouter(
    prefix="/account/v1",
    tags=["account"],
)

_service = get_service(AccountService, db_dependency=get_rls_db)


@router.get("/")
def get_account(
    ctx: TokenContext = Depends(require_permission(resource="own_account", action="r", allow_deactivated=True)),
    service: AccountService = Depends(_service),
) -> ApiResponse[AccountResponse]:
    return ApiResponse(ok=True, msg="Fetched Account", data=service.get(user_id=ctx.user_id, location_id=ctx.location_id))


@router.post("/password")
def change_password(
    body: ChangePasswordRequest,
    ctx: TokenContext = Depends(require_permission(resource="own_account", action="u")),
    service: AccountService = Depends(_service),
) -> ApiResponse[None]:
    service.change_password(user_id=ctx.user_id, location_id=ctx.location_id, body=body)

    return ApiResponse(ok=True, msg="Password changed", data=None)


@router.post("/deactivate")
def deactivate_account(
    body: DeactivateAccountRequest,
    ctx: TokenContext = Depends(require_permission(resource="own_account", action="u")),
    service: AccountService = Depends(_service),
) -> ApiResponse[None]:
    service.deactivate(user_id=ctx.user_id, location_id=ctx.location_id, body=body)

    return ApiResponse(ok=True, msg="Account deactivated", data=None)


@router.post("/reactivation-request")
def request_reactivation(
    ctx: TokenContext = Depends(require_permission(resource="own_account", action="u", allow_deactivated=True)),
    service: AccountService = Depends(_service),
) -> ApiResponse[None]:
    service.request_reactivation(user_id=ctx.user_id, location_id=ctx.location_id)

    return ApiResponse(ok=True, msg="Request sent", data=None)
