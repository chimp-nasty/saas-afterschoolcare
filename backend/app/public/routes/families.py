from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.schemas.booking import FamilyBookingResponse
from app.public.schemas.customer import UpdateContactDetailsRequest
from app.public.schemas.families import (
    FamilyAttendanceResponse,
    FamilyDateRangeRequest,
    FamilyPaymentResponse,
    FamilyResponse,
    FamilySearchFilterRequest,
    FamilySearchResultResponse,
    ReactivationRequestResponse,
)
from app.public.schemas.family_notes import (
    ChildNoteResponse,
    CreateChildNoteRequest,
    FamilyMessageResponse,
    SendFamilyMessageRequest,
)
from app.public.services.families import FamilyService
from app.public.services.family_notes import ChildNoteService, FamilyMessageService


# Admin › Families (slice 4-4). families r: find a family and see its page,
# bookings, attendance history and payments; families u: correct its phone
# and address. Admins and superadmins only: families hold customer_profile
# and bookings permissions for their own records, so these use their own.
# Refunds go through POST /refunds/v1/ (refunds c).
#
# Deactivated accounts (docs/account-deactivation.md): families r lists the
# families asking to be reactivated (the admin home counts them); families u
# reactivates one.
#
# Notes and messages (slice 4-5), admins and superadmins:
#   child_notes r/c/d: staff's notes about the children, never shown to
#     the family (staff read them at the staff kiosk);
#   families r: the messages sent to the family (their own come through
#     /action/v1, actions r, which families hold too); actions c/d: send
#     one, withdraw one until it's read.
router = APIRouter(
    prefix="/families/v1",
    tags=["families"],
)

_service = get_service(FamilyService, db_dependency=get_rls_db)
_notes = get_service(ChildNoteService, db_dependency=get_rls_db)
_messages = get_service(FamilyMessageService, db_dependency=get_rls_db)


@router.get("/")
def search_families(
    filters: Annotated[FamilySearchFilterRequest, Query()],
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[list[FamilySearchResultResponse]]:
    return ApiResponse(ok=True, msg="Found families", data=service.search(location_id=ctx.location_id, text=filters.q))


# Before /{user_id}, which would take "reactivation-requests" as an id.
@router.get("/reactivation-requests")
def list_reactivation_requests(
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[list[ReactivationRequestResponse]]:
    return ApiResponse(ok=True, msg="Fetched reactivation requests", data=service.reactivation_requests(location_id=ctx.location_id))


@router.post("/{user_id}/reactivate")
def reactivate_family(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="families", action="u")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[FamilyResponse]:
    return ApiResponse(ok=True, msg="Family reactivated", data=service.reactivate(location_id=ctx.location_id, user_id=user_id))


@router.get("/{user_id}")
def get_family(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[FamilyResponse]:
    return ApiResponse(ok=True, msg="Fetched family", data=service.get(location_id=ctx.location_id, user_id=user_id))


@router.patch("/{user_id}")
def update_family(
    user_id: UUID,
    body: UpdateContactDetailsRequest,
    ctx: TokenContext = Depends(require_permission(resource="families", action="u")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[FamilyResponse]:
    return ApiResponse(ok=True, msg="Family details saved", data=service.update(location_id=ctx.location_id, user_id=user_id, body=body))


@router.get("/{user_id}/bookings")
def list_family_bookings(
    user_id: UUID,
    dates: Annotated[FamilyDateRangeRequest, Query()],
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[list[FamilyBookingResponse]]:
    return ApiResponse(ok=True, msg="Fetched bookings", data=service.bookings(location_id=ctx.location_id, user_id=user_id, dates=dates))


@router.get("/{user_id}/attendance")
def list_family_attendance(
    user_id: UUID,
    dates: Annotated[FamilyDateRangeRequest, Query()],
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[list[FamilyAttendanceResponse]]:
    return ApiResponse(ok=True, msg="Fetched attendance", data=service.attendance(location_id=ctx.location_id, user_id=user_id, dates=dates))


@router.get("/{user_id}/payments")
def list_family_payments(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyService = Depends(_service),
) -> ApiResponse[list[FamilyPaymentResponse]]:
    return ApiResponse(ok=True, msg="Fetched payments", data=service.payments(location_id=ctx.location_id, user_id=user_id))


@router.get("/{user_id}/notes")
def list_family_notes(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="child_notes", action="r")),
    service: ChildNoteService = Depends(_notes),
) -> ApiResponse[list[ChildNoteResponse]]:
    return ApiResponse(ok=True, msg="Fetched notes", data=service.list_for_family(location_id=ctx.location_id, user_id=user_id))


@router.post("/{user_id}/notes", status_code=201)
def add_family_note(
    user_id: UUID,
    body: CreateChildNoteRequest,
    ctx: TokenContext = Depends(require_permission(resource="child_notes", action="c")),
    service: ChildNoteService = Depends(_notes),
) -> ApiResponse[ChildNoteResponse]:
    return ApiResponse(
        ok=True,
        msg="Note added",
        data=service.create(location_id=ctx.location_id, user_id=user_id, writer_id=ctx.user_id, body=body),
    )


@router.delete("/{user_id}/notes/{note_id}")
def delete_family_note(
    user_id: UUID,
    note_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="child_notes", action="d")),
    service: ChildNoteService = Depends(_notes),
) -> ApiResponse[None]:
    service.delete(location_id=ctx.location_id, user_id=user_id, note_id=note_id)

    return ApiResponse(ok=True, msg="Note deleted", data=None)


@router.get("/{user_id}/messages")
def list_family_messages(
    user_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="families", action="r")),
    service: FamilyMessageService = Depends(_messages),
) -> ApiResponse[list[FamilyMessageResponse]]:
    return ApiResponse(ok=True, msg="Fetched messages", data=service.list(location_id=ctx.location_id, user_id=user_id))


@router.post("/{user_id}/messages", status_code=201)
def send_family_message(
    user_id: UUID,
    body: SendFamilyMessageRequest,
    ctx: TokenContext = Depends(require_permission(resource="actions", action="c")),
    service: FamilyMessageService = Depends(_messages),
) -> ApiResponse[FamilyMessageResponse]:
    return ApiResponse(
        ok=True,
        msg="Message sent",
        data=service.send(location_id=ctx.location_id, user_id=user_id, sender_id=ctx.user_id, body=body),
    )


@router.delete("/{user_id}/messages/{message_id}")
def withdraw_family_message(
    user_id: UUID,
    message_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="actions", action="d")),
    service: FamilyMessageService = Depends(_messages),
) -> ApiResponse[None]:
    service.withdraw(location_id=ctx.location_id, user_id=user_id, message_id=message_id)

    return ApiResponse(ok=True, msg="Message withdrawn", data=None)
