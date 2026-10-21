from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.service import get_service
from app.kiosk.dependencies import (
    KioskDevice,
    KioskStaff,
    require_kiosk_device,
    require_kiosk_staff,
)
from app.kiosk.schemas.kiosk import KioskInfoResponse
from app.kiosk.schemas.staff_kiosk import (
    StaffKioskBulkRequest,
    StaffKioskCheckIdRequest,
    StaffKioskMemberResponse,
    StaffKioskShiftRequest,
    StaffKioskSignRequest,
    StaffKioskUndoRequest,
    StaffKioskVerifyResponse,
)
from app.kiosk.services.staff_kiosk import StaffKioskService
from app.public.schemas.attendance import (
    AttendanceTimesResponse,
    RollPickupPersonResponse,
    RollResponse,
    RunSheetResponse,
    StaffShiftResponse,
)
from app.public.schemas.booking import FamilyBookingResponse
from app.public.schemas.child_documents import ChildDocumentDownloadResponse
from app.public.schemas.children import ChildSearchResultResponse
from app.public.schemas.refunds import CreateRefundRequest, RefundResponse
from app.public.schemas.child_medical import ActionPlanResponse, ChildMedicalResponse, SetPrintedRequest
from app.public.services.attendance import ReadAttendanceService, UpdateAttendanceService
from app.public.services.bookings_read import ReadFamilyBookingsService
from app.public.services.children_read import ReadChildService
from app.public.services.refunds_create import CreateRefundService
from app.public.services.child_documents_read import ReadChildDocumentService
from app.public.services.child_medical_read import ActionPlanPrintService, ReadChildMedicalService
from app.public.services.pickup_identity import PickupIdentityService
from app.public.services.staff_shifts import StaffShiftService


# The staff kiosk (operations, docs/portals.md). Nobody is logged in: the
# paired device alone shows what it is, the staff list and the run sheet
# without personal details. Every other request carries a staff member and
# their PIN (X-Kiosk-Staff, X-Kiosk-Pin); require_kiosk_staff checks them
# and the permission on the kiosk channel, then the normal services run as
# that staff member. Each route's comment names its permission.
router = APIRouter(
    prefix="/staff-kiosk/v1/{location_code}",
    tags=["staff-kiosk"],
)

_device = require_kiosk_device("staff")


def _service(service):
    # Kiosk requests use the plain session; require_kiosk_staff sets RLS on it.
    return get_service(service, db_dependency=get_db)


# ---------------------------------------------------------------------------
# Before anyone enters a PIN (the device only)
# ---------------------------------------------------------------------------

@router.get("/device")
def get_staff_kiosk_device(
    device: KioskDevice = Depends(_device),
    service: StaffKioskService = Depends(_service(StaffKioskService)),
) -> ApiResponse[KioskInfoResponse]:
    return ApiResponse(ok=True, msg="Fetched Kiosk", data=service.describe(device=device))


@router.get("/staff")
def list_kiosk_staff(
    device: KioskDevice = Depends(_device),
    service: StaffKioskService = Depends(_service(StaffKioskService)),
) -> ApiResponse[list[StaffKioskMemberResponse]]:
    return ApiResponse(ok=True, msg="Fetched Staff", data=service.staff(device=device))


@router.get("/board")
def get_staff_kiosk_board(
    on: date | None = Query(default=None, alias="date"),
    device: KioskDevice = Depends(_device),
    service: StaffKioskService = Depends(_service(StaffKioskService)),
) -> ApiResponse[RunSheetResponse]:
    return ApiResponse(ok=True, msg="Fetched Run Sheet", data=service.board(device=device, on=on))


# ---------------------------------------------------------------------------
# With a staff member's PIN
# ---------------------------------------------------------------------------

# Checks a PIN at the start of a task (attendance_records r: every staff
# role has it at the kiosk).
@router.post("/verify")
def verify_staff_pin(
    staff: KioskStaff = Depends(require_kiosk_staff(resource="attendance_records", action="r")),
    service: StaffKioskService = Depends(_service(StaffKioskService)),
) -> ApiResponse[StaffKioskVerifyResponse]:
    result = service.verify(device=staff.device, user_id=staff.user_id)

    return ApiResponse(ok=True, msg=f"Hi {result.first_name}", data=result)


# The run sheet with families' contacts and pickup lists (attendance_records r).
@router.get("/roll")
def get_staff_kiosk_roll(
    on: date | None = Query(default=None, alias="date"),
    staff: KioskStaff = Depends(require_kiosk_staff(resource="attendance_records", action="r")),
    service: ReadAttendanceService = Depends(_service(ReadAttendanceService)),
) -> ApiResponse[RollResponse]:
    return ApiResponse(ok=True, msg="Fetched Roll", data=service.roll(location_id=staff.device.location_id, on=on))


# A family's pickup list (authorized_pickup_persons r).
@router.get("/families/{family_user_id}/pickups")
def get_family_pickups(
    family_user_id: UUID,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="authorized_pickup_persons", action="r")),
    service: ReadAttendanceService = Depends(_service(ReadAttendanceService)),
) -> ApiResponse[list[RollPickupPersonResponse]]:
    return ApiResponse(
        ok=True,
        msg="Fetched Pickups",
        data=service.family_pickups(location_id=staff.device.location_id, family_user_id=family_user_id),
    )


# Find a family by a child's name (child_profile r).
@router.get("/children/search")
def search_children(
    q: str = Query(min_length=2, max_length=100),
    staff: KioskStaff = Depends(require_kiosk_staff(resource="child_profile", action="r")),
    service: ReadChildService = Depends(_service(ReadChildService)),
) -> ApiResponse[list[ChildSearchResultResponse]]:
    return ApiResponse(ok=True, msg="Found Children", data=service.search(location_id=staff.device.location_id, text=q))


# A family's bookings: today to 2 weeks ahead, and anything unpaid
# (bookings r).
@router.get("/families/{family_user_id}/bookings")
def list_family_bookings(
    family_user_id: UUID,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="bookings", action="r")),
    service: ReadFamilyBookingsService = Depends(_service(ReadFamilyBookingsService)),
) -> ApiResponse[list[FamilyBookingResponse]]:
    return ApiResponse(
        ok=True,
        msg="Fetched Bookings",
        data=service.list(location_id=staff.device.location_id, family_user_id=family_user_id),
    )


# Refund one booking in full (refunds c: admins only at the kiosk). The
# database allows it up to and including the session day.
@router.post("/refunds", status_code=201)
def create_kiosk_refund(
    body: CreateRefundRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="refunds", action="c")),
    service: CreateRefundService = Depends(_service(CreateRefundService)),
) -> ApiResponse[RefundResponse]:
    result = service.create(
        booking_id=body.booking_id,
        user_id=staff.user_id,
        location_id=staff.device.location_id,
        kiosk_device_id=staff.device.device_id,
    )

    return ApiResponse(ok=True, msg="Refund requested", data=result)


# A child's medical details, review status and documents
# (child_medical_state r).
@router.get("/children/{child_id}/medical")
def get_child_medical(
    child_id: UUID,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="child_medical_state", action="r")),
    service: ReadChildMedicalService = Depends(_service(ReadChildMedicalService)),
) -> ApiResponse[ChildMedicalResponse]:
    return ApiResponse(ok=True, msg="Fetched Medical Details", data=service.get(child_id=child_id))


# The location's action plans, for the physical folder (child_documents r).
@router.get("/action-plans")
def list_action_plans(
    staff: KioskStaff = Depends(require_kiosk_staff(resource="child_documents", action="r")),
    service: ReadChildMedicalService = Depends(_service(ReadChildMedicalService)),
) -> ApiResponse[list[ActionPlanResponse]]:
    return ApiResponse(ok=True, msg="Fetched Action Plans", data=service.action_plans(location_id=staff.device.location_id))


# A short-lived link to view or print a document (child_documents r).
@router.get("/documents/{document_id}/download")
def get_document_download(
    document_id: UUID,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="child_documents", action="r")),
    service: ReadChildDocumentService = Depends(_service(ReadChildDocumentService)),
) -> ApiResponse[ChildDocumentDownloadResponse]:
    return ApiResponse(ok=True, msg="Fetched Download", data=service.create_download(id=document_id))


# Tick (or untick) that a plan's been printed for the folder
# (child_document_prints u: staff, admins and superadmins at the kiosk).
@router.put("/documents/{document_id}/printed")
def set_document_printed(
    document_id: UUID,
    body: SetPrintedRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="child_document_prints", action="u")),
    service: ActionPlanPrintService = Depends(_service(ActionPlanPrintService)),
) -> ApiResponse[None]:
    service.set_printed(document_id=document_id, printed=body.printed)

    return ApiResponse(ok=True, msg="Marked printed" if body.printed else "Marked not printed", data=None)


# Sign a child in or out (attendance_records u).
@router.post("/sign")
def staff_kiosk_sign(
    body: StaffKioskSignRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="attendance_records", action="u")),
    service: UpdateAttendanceService = Depends(_service(UpdateAttendanceService)),
) -> ApiResponse[AttendanceTimesResponse]:
    if body.action == "in":
        result = service.sign_in(booking_id=body.booking_id, at=body.at)
    else:
        result = service.sign_out(
            booking_id=body.booking_id,
            at=body.at,
            collected_by_pickup_person_id=body.collected_by_pickup_person_id,
            released_to_name=body.released_to_name,
            release_note=body.release_note,
            sent_to_school=body.sent_to_school,
        )

    return ApiResponse(ok=True, msg="Signed in" if body.action == "in" else "Signed out", data=result)


# Several children at once, all or nothing (attendance_records u): a
# session's arrivals, a before school session sent to school (the database
# allows that only for before school care), or brothers and sisters signed
# out to the same person.
@router.post("/bulk")
def staff_kiosk_bulk(
    body: StaffKioskBulkRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="attendance_records", action="u")),
    service: UpdateAttendanceService = Depends(_service(UpdateAttendanceService)),
) -> ApiResponse[list[AttendanceTimesResponse]]:
    if body.action == "sign_in":
        result = service.sign_in_many(booking_ids=body.booking_ids, at=body.at)
        msg = f"{len(result)} signed in"
    elif body.action == "to_school":
        result = service.send_to_school(booking_ids=body.booking_ids, at=body.at)
        msg = f"{len(result)} sent to school"
    else:
        result = service.sign_out_many(
            booking_ids=body.booking_ids,
            at=body.at,
            collected_by_pickup_person_id=body.collected_by_pickup_person_id,
            released_to_name=body.released_to_name,
            release_note=body.release_note,
        )
        msg = f"{len(result)} signed out"

    return ApiResponse(ok=True, msg=msg, data=result)


# Correct a mistake (attendance_records u).
@router.post("/undo")
def staff_kiosk_undo(
    body: StaffKioskUndoRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="attendance_records", action="u")),
    service: UpdateAttendanceService = Depends(_service(UpdateAttendanceService)),
) -> ApiResponse[AttendanceTimesResponse]:
    return ApiResponse(ok=True, msg="Undone", data=service.undo(booking_id=body.booking_id, step=body.step))


# Check a pickup person's ID, or approve them without ID (pickup_identity u).
@router.post("/check-id")
def staff_kiosk_check_id(
    body: StaffKioskCheckIdRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="pickup_identity", action="u")),
    service: PickupIdentityService = Depends(_service(PickupIdentityService)),
) -> ApiResponse[RollPickupPersonResponse]:
    result = service.check(pickup_person_id=body.pickup_person_id, staff_user_id=staff.user_id, id_seen=body.id_seen)

    return ApiResponse(ok=True, msg="ID checked" if body.id_seen else "Approved", data=result)


# Start or end your own shift (staff_shifts c). The one action that doesn't
# need you to be on shift already.
@router.post("/shift")
def staff_kiosk_shift(
    body: StaffKioskShiftRequest,
    staff: KioskStaff = Depends(require_kiosk_staff(resource="staff_shifts", action="c", on_shift=False)),
    service: StaffShiftService = Depends(_service(StaffShiftService)),
) -> ApiResponse[StaffShiftResponse]:
    where = {"location_id": staff.device.location_id, "user_id": staff.user_id, "device_id": staff.device.device_id}

    if body.action == "start":
        result = service.start(**where, previous_shift_ended_at=body.previous_shift_ended_at)
    else:
        result = service.end(**where)

    return ApiResponse(ok=True, msg="Shift started" if body.action == "start" else "Shift ended", data=result)
