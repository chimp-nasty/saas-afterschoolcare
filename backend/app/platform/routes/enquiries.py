from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.platform import (
    PlatformContext,
    get_platform_context,
    get_platform_db,
    require_platform_site,
)
from app.dependencies.service import get_service
from app.platform.schemas.enquiries import PlatformEnquiryResponse, SubmitPlatformEnquiryRequest
from app.platform.services.platform_enquiries import PlatformEnquiryService


# Enquiries to the platform itself (docs/platform-site.md), on the
# platform's own site only.
#   POST /: anyone, from the contact page; no login (rate limited per
#     address, app/middleware/__init__.py).
#   The rest: the platform's admins (their own login, get_platform_context).
router = APIRouter(
    prefix="/platform-enquiries/v1",
    tags=["platform"],
    dependencies=[Depends(require_platform_site)],
)

_public = get_service(PlatformEnquiryService, db_dependency=get_db)
_service = get_service(PlatformEnquiryService, db_dependency=get_platform_db)


@router.post("/", status_code=201)
def submit_platform_enquiry(
    body: SubmitPlatformEnquiryRequest,
    service: PlatformEnquiryService = Depends(_public),
) -> ApiResponse[None]:
    service.submit(body=body)

    return ApiResponse(ok=True, msg="Message sent", data=None)


@router.get("/")
def list_platform_enquiries(
    closed: bool = False,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformEnquiryService = Depends(_service),
) -> ApiResponse[list[PlatformEnquiryResponse]]:
    return ApiResponse(ok=True, msg="Fetched enquiries", data=service.list(closed=closed))


@router.post("/{enquiry_id}/close")
def close_platform_enquiry(
    enquiry_id: UUID,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformEnquiryService = Depends(_service),
) -> ApiResponse[PlatformEnquiryResponse]:
    return ApiResponse(ok=True, msg="Enquiry closed", data=service.set_closed(id=enquiry_id, closed=True))


@router.post("/{enquiry_id}/reopen")
def reopen_platform_enquiry(
    enquiry_id: UUID,
    _: PlatformContext = Depends(get_platform_context),
    service: PlatformEnquiryService = Depends(_service),
) -> ApiResponse[PlatformEnquiryResponse]:
    return ApiResponse(ok=True, msg="Enquiry reopened", data=service.set_closed(id=enquiry_id, closed=False))
