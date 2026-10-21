from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.response import ApiResponse
from app.dependencies.auth import resolve_location_id
from app.dependencies.db import get_db
from app.dependencies.service import get_service
from app.kiosk.dependencies import (
    KioskDevice,
    KioskSession,
    require_kiosk_device,
    require_kiosk_session,
    set_device_cookie,
)
from app.kiosk.schemas.kiosk import (
    KioskChangePinRequest,
    KioskInfoResponse,
    KioskForgotPinRequest,
    KioskLoginRequest,
    KioskLoginResponse,
    KioskPairRequest,
    KioskSessionResponse,
    KioskSignRequest,
    KioskSignResponse,
    KioskTodayResponse,
)
from app.kiosk.services.family_kiosk import FamilyKioskService


# The family kiosk: a paired tablet, not a logged-in user, so no
# permissions here. The device cookie (and, for a person's own actions,
# their session token) is the credential; every request is checked by
# require_kiosk_device / require_kiosk_session. Rate limited per tablet
# rather than per person (app/middleware/__init__.py).
router = APIRouter(
    prefix="/kiosk/v1/{location_code}",
    tags=["kiosk"],
)

_service = get_service(FamilyKioskService, db_dependency=get_db)


# Pairing works for both kinds of kiosk: the setup code says which.
@router.post("/pair")
def pair_kiosk(
    body: KioskPairRequest,
    response: Response,
    location_id: UUID = Depends(resolve_location_id),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[KioskInfoResponse]:
    token, device = service.pair(location_id=location_id, code=body.code)

    set_device_cookie(response, token)

    return ApiResponse(ok=True, msg="Kiosk set up", data=device)


@router.get("/device")
def get_kiosk_device(
    device: KioskDevice = Depends(require_kiosk_device("family")),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[KioskInfoResponse]:
    return ApiResponse(ok=True, msg="Fetched Kiosk", data=service.describe(device=device))


@router.post("/login")
def kiosk_login(
    body: KioskLoginRequest,
    device: KioskDevice = Depends(require_kiosk_device("family")),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[KioskLoginResponse]:
    result = service.login(device=device, phone=body.phone, pin=body.pin)

    return ApiResponse(ok=True, msg=f"Hi {result.first_name}", data=result)


@router.post("/pin")
def kiosk_change_pin(
    body: KioskChangePinRequest,
    session: KioskSession = Depends(require_kiosk_session("family", allow_pin_change=True)),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[KioskSessionResponse]:
    result = service.change_pin(session=session, new_pin=body.new_pin)

    return ApiResponse(ok=True, msg="PIN changed", data=result)


@router.post("/forgot-pin")
def kiosk_forgot_pin(
    body: KioskForgotPinRequest,
    device: KioskDevice = Depends(require_kiosk_device("family")),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[None]:
    service.forgot_pin(device=device, phone=body.phone)

    # The same reply whoever asked, so the kiosk can't be used to find out
    # which numbers are registered.
    return ApiResponse(
        ok=True,
        msg="If that number is registered, we've emailed a new PIN to its email address.",
        data=None,
    )


@router.get("/today")
def kiosk_today(
    session: KioskSession = Depends(require_kiosk_session("family")),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[KioskTodayResponse]:
    return ApiResponse(ok=True, msg="Fetched Today", data=service.today(session=session))


@router.post("/sign")
def kiosk_sign(
    body: KioskSignRequest,
    session: KioskSession = Depends(require_kiosk_session("family")),
    service: FamilyKioskService = Depends(_service),
) -> ApiResponse[KioskSignResponse]:
    result = service.sign(session=session, booking_id=body.booking_id, action=body.action)

    return ApiResponse(
        ok=True,
        msg="Signed in" if body.action == "in" else "Signed out",
        data=result,
    )
