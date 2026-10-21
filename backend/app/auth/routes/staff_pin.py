from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.auth.schemas.staff_pin import SetStaffPinRequest, StaffPinStatusResponse
from app.auth.services.staff_pin import StaffPinService
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service


# Your own staff kiosk PIN: staff_pins u (staff, admin, superadmin), since
# reading and setting it are the same act of managing your PIN. Setting it
# needs your password too, and is rate limited (app/middleware/__init__.py).
router = APIRouter(
    prefix="/staff-pin/v1",
    tags=["staff-pin"],
)

_service = get_service(StaffPinService, db_dependency=get_rls_db)


@router.get("/")
def get_staff_pin_status(
    ctx: TokenContext = Depends(require_permission(resource="staff_pins", action="u")),
    service: StaffPinService = Depends(_service),
) -> ApiResponse[StaffPinStatusResponse]:
    return ApiResponse(ok=True, msg="Fetched Staff PIN", data=service.status(user_id=ctx.user_id))


@router.put("/")
def set_staff_pin(
    body: SetStaffPinRequest,
    ctx: TokenContext = Depends(require_permission(resource="staff_pins", action="u")),
    service: StaffPinService = Depends(_service),
) -> ApiResponse[StaffPinStatusResponse]:
    return ApiResponse(ok=True, msg="Staff PIN saved", data=service.set(user_id=ctx.user_id, body=body))
