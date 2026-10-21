from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.kiosk_devices import KioskDeviceService
from app.public.schemas.kiosk_devices import (
    CreateKioskDeviceRequest,
    KioskDeviceResponse,
    KioskSettingsResponse,
    KioskSetupCodeResponse,
    UpdateKioskSettingsRequest,
)


# The location's kiosk tablets. Admins add, re-pair and revoke them
# (location_kiosk_devices c / u / d, admin and superadmin only); staff can
# see them (r). RLS also limits writes to the location's admins.
router = APIRouter(
    prefix="/kiosk-devices/v1",
    tags=["kiosk-devices"],
)

_service = get_service(KioskDeviceService, db_dependency=get_rls_db)


@router.get("/")
def list_kiosk_devices(
    ctx: TokenContext = Depends(require_permission(resource="location_kiosk_devices", action="r")),
    service: KioskDeviceService = Depends(_service),
) -> ApiResponse[list[KioskDeviceResponse]]:
    return ApiResponse(
        ok=True,
        msg="Fetched Kiosks",
        data=service.list_for_location(location_id=ctx.location_id),
    )


# The location's kiosk rules: whether children can be signed in and out
# only around each session. Read with location_kiosk_devices r, changed with u
# (admins; public.set_kiosk_enforce_service_times also checks).
@router.get("/settings")
def get_kiosk_settings(
    ctx: TokenContext = Depends(require_permission(resource="location_kiosk_devices", action="r")),
    service: KioskDeviceService = Depends(_service),
) -> ApiResponse[KioskSettingsResponse]:
    return ApiResponse(ok=True, msg="Fetched Kiosk Settings", data=service.settings(location_id=ctx.location_id))


@router.put("/settings")
def update_kiosk_settings(
    body: UpdateKioskSettingsRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_kiosk_devices", action="u")),
    service: KioskDeviceService = Depends(_service),
) -> ApiResponse[KioskSettingsResponse]:
    return ApiResponse(
        ok=True,
        msg="Kiosk settings saved",
        data=service.update_settings(location_id=ctx.location_id, body=body),
    )


@router.post("/", status_code=201)
def create_kiosk_device(
    body: CreateKioskDeviceRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_kiosk_devices", action="c")),
    service: KioskDeviceService = Depends(_service),
) -> ApiResponse[KioskSetupCodeResponse]:
    return ApiResponse(
        ok=True,
        msg="Kiosk added",
        data=service.create(location_id=ctx.location_id, body=body),
    )


@router.post("/{device_id}/setup-code")
def new_kiosk_setup_code(
    device_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="location_kiosk_devices", action="u")),
    service: KioskDeviceService = Depends(_service),
) -> ApiResponse[KioskSetupCodeResponse]:
    return ApiResponse(
        ok=True,
        msg="New setup code",
        data=service.new_setup_code(id=device_id),
    )


@router.post("/{device_id}/revoke")
def revoke_kiosk_device(
    device_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="location_kiosk_devices", action="d")),
    service: KioskDeviceService = Depends(_service),
) -> ApiResponse[KioskDeviceResponse]:
    return ApiResponse(
        ok=True,
        msg="Kiosk revoked",
        data=service.revoke(id=device_id),
    )
