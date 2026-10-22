from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.auth.schemas.staff_accounts import (
    AddStaffRequest,
    AddStaffResponse,
    ChangeStaffRoleRequest,
    RenameStaffRequest,
    StaffAccountResponse,
)
from app.auth.services.staff_accounts import StaffAccountService
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service


# Admin › Staff (slice 4-3). staff_accounts r/c/u: admins and superadmins
# (see, add staff, resend invites, correct names, reset staff PINs);
# staff_accounts d and staff_admin_roles u: superadmins (remove people,
# make or unmake admins). Each route's comment names its permission.
router = APIRouter(
    prefix="/staff-accounts/v1",
    tags=["staff-accounts"],
)

_service = get_service(StaffAccountService, db_dependency=get_rls_db)


# Everyone who works at the location (staff_accounts r).
@router.get("/")
def list_staff(
    ctx: TokenContext = Depends(require_permission(resource="staff_accounts", action="r")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[list[StaffAccountResponse]]:
    return ApiResponse(ok=True, msg="Fetched staff", data=service.list(location_id=ctx.location_id))


# Add someone (staff_accounts c; as an admin, staff_admin_roles u too).
@router.post("/", status_code=201)
def add_staff(
    body: AddStaffRequest,
    ctx: TokenContext = Depends(require_permission(resource="staff_accounts", action="c")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[AddStaffResponse]:
    result = service.add(
        location_id=ctx.location_id,
        body=body,
        can_make_admins="u" in ctx.permissions.get("staff_admin_roles", frozenset()),
    )

    return ApiResponse(ok=True, msg="Invite sent" if result.invited else "Added to this centre", data=result)


# A new invite link for someone who hasn't logged in yet (staff_accounts u).
@router.post("/{user_id}/invite")
def resend_invite(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="staff_accounts", action="u")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[StaffAccountResponse]:
    return ApiResponse(ok=True, msg="Invite sent", data=service.resend_invite(location_id=ctx.location_id, user_id=user_id))


# Correct a name (staff_accounts u).
@router.patch("/{user_id}")
def rename_staff(
    user_id: UUID,
    body: RenameStaffRequest,
    ctx: TokenContext = Depends(require_permission(resource="staff_accounts", action="u")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[StaffAccountResponse]:
    return ApiResponse(ok=True, msg="Name saved", data=service.rename(location_id=ctx.location_id, user_id=user_id, body=body))


# Staff <-> admin (staff_admin_roles u: superadmins).
@router.put("/{user_id}/role")
def change_staff_role(
    user_id: UUID,
    body: ChangeStaffRoleRequest,
    ctx: TokenContext = Depends(require_permission(resource="staff_admin_roles", action="u")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[StaffAccountResponse]:
    return ApiResponse(ok=True, msg="Role changed", data=service.change_role(location_id=ctx.location_id, user_id=user_id, body=body))


# Clear their staff kiosk PIN; they set a new one on their account page
# (staff_accounts u).
@router.post("/{user_id}/reset-pin")
def reset_staff_pin(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="staff_accounts", action="u")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[StaffAccountResponse]:
    return ApiResponse(ok=True, msg="Staff PIN reset", data=service.reset_pin(location_id=ctx.location_id, user_id=user_id))


# Remove from this location's staff (staff_accounts d: superadmins).
@router.delete("/{user_id}")
def remove_staff(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="staff_accounts", action="d")),
    service: StaffAccountService = Depends(_service),
) -> ApiResponse[None]:
    service.remove(location_id=ctx.location_id, user_id=user_id)

    return ApiResponse(ok=True, msg="Removed from this centre", data=None)
