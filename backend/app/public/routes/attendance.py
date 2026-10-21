from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.schemas.attendance import RollResponse, RunSheetResponse
from app.public.services.attendance import ReadAttendanceService


# The admin run sheet: read-only (attendance_records r on the web, admins
# only; attendance_roll also returns nothing to anyone else). Attendance is
# changed only at the kiosks, so there are no write endpoints here. The
# staff kiosk reads the same roll through the same service.
router = APIRouter(
    prefix="/attendance/v1",
    tags=["attendance"],
)


@router.get("/roll")
def get_roll(
    on: date | None = Query(default=None, alias="date"),
    ctx: TokenContext = Depends(require_permission(resource="attendance_records", action="r")),
    service: ReadAttendanceService = Depends(get_service(ReadAttendanceService, db_dependency=get_rls_db)),
) -> ApiResponse[RollResponse]:
    return ApiResponse(ok=True, msg="Fetched Roll", data=service.roll(location_id=ctx.location_id, on=on))


# The run sheet as the staff kiosk shows it (sessions, places, who and when),
# read-only for admins (attendance_records r, as the roll).
@router.get("/board")
def get_run_sheet(
    on: date | None = Query(default=None, alias="date"),
    ctx: TokenContext = Depends(require_permission(resource="attendance_records", action="r")),
    service: ReadAttendanceService = Depends(get_service(ReadAttendanceService, db_dependency=get_rls_db)),
) -> ApiResponse[RunSheetResponse]:
    return ApiResponse(ok=True, msg="Fetched Run Sheet", data=service.run_sheet(location_id=ctx.location_id, on=on))
