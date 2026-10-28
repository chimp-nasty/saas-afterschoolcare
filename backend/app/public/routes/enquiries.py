from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission, resolve_location_id
from app.dependencies.db import get_db
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.schemas.enquiries import (
    EnquiryReplyRequest,
    EnquiryResponse,
    EnquirySummaryResponse,
    SubmitEnquiryRequest,
)
from app.public.services.enquiries import EnquiryService


# Contact form enquiries (docs/enquiries.md).
#   POST /{location_code}/submit: anyone, logged in or not, from the
#     centre's page; no permission (rate limited per address,
#     app/middleware/__init__.py; the database takes it in through
#     public.submit_enquiry).
#   enquiries r: the centre's admins and superadmins read the inbox.
#   enquiries u: they reply (emailed to the person), close and reopen.
router = APIRouter(
    prefix="/enquiries/v1",
    tags=["enquiries"],
)

_public = get_service(EnquiryService, db_dependency=get_db)
_service = get_service(EnquiryService, db_dependency=get_rls_db)


@router.post("/{location_code}/submit", status_code=201)
def submit_enquiry(
    body: SubmitEnquiryRequest,
    location_id: UUID = Depends(resolve_location_id),
    service: EnquiryService = Depends(_public),
) -> ApiResponse[None]:
    service.submit(location_id=location_id, body=body)

    return ApiResponse(ok=True, msg="Message sent", data=None)


@router.get("/")
def list_enquiries(
    status: Literal["open", "new", "replied", "closed", "all"] = "open",
    ctx: TokenContext = Depends(require_permission(resource="enquiries", action="r")),
    service: EnquiryService = Depends(_service),
) -> ApiResponse[list[EnquirySummaryResponse]]:
    return ApiResponse(ok=True, msg="Fetched enquiries", data=service.list(location_id=ctx.location_id, status=status))


@router.get("/{enquiry_id}")
def get_enquiry(
    enquiry_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="enquiries", action="r")),
    service: EnquiryService = Depends(_service),
) -> ApiResponse[EnquiryResponse]:
    return ApiResponse(ok=True, msg="Fetched enquiry", data=service.get(location_id=ctx.location_id, id=enquiry_id))


@router.post("/{enquiry_id}/reply")
def reply_to_enquiry(
    enquiry_id: UUID,
    body: EnquiryReplyRequest,
    ctx: TokenContext = Depends(require_permission(resource="enquiries", action="u")),
    service: EnquiryService = Depends(_service),
) -> ApiResponse[EnquiryResponse]:
    return ApiResponse(ok=True, msg="Reply sent", data=service.reply(location_id=ctx.location_id, id=enquiry_id, body=body))


@router.post("/{enquiry_id}/close")
def close_enquiry(
    enquiry_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="enquiries", action="u")),
    service: EnquiryService = Depends(_service),
) -> ApiResponse[EnquiryResponse]:
    return ApiResponse(ok=True, msg="Enquiry closed", data=service.close(location_id=ctx.location_id, id=enquiry_id))


@router.post("/{enquiry_id}/reopen")
def reopen_enquiry(
    enquiry_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="enquiries", action="u")),
    service: EnquiryService = Depends(_service),
) -> ApiResponse[EnquiryResponse]:
    return ApiResponse(ok=True, msg="Enquiry reopened", data=service.reopen(location_id=ctx.location_id, id=enquiry_id))
