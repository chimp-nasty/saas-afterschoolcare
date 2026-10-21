import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import LocationKioskDevice
from app.db.transaction import transactional
from app.errors.kiosk import KioskDeviceNotFoundError
from app.public.repositories.location_kiosk_device import LocationKioskDeviceRepository
from app.public.schemas.kiosk_devices import (
    CreateKioskDeviceRequest,
    KioskDeviceResponse,
    KioskSettingsResponse,
    KioskSetupCodeResponse,
    UpdateKioskSettingsRequest,
)


logger = logging.getLogger("app.kiosk")

# Uppercase letters and digits without lookalikes (0/O, 1/I/L), so a code
# is easy to read off a screen and type on a tablet.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8
SETUP_CODE_LIFETIME = timedelta(minutes=15)


def _new_code() -> tuple[str, str]:
    """A setup code, and the hash stored for it (kiosk_pair compares)."""
    code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))

    return code, hashlib.sha256(code.encode()).hexdigest()


class KioskDeviceService:
    """
    An admin managing their location's two kiosk tablets: at most one active
    family kiosk and one staff kiosk (uq_location_kiosk_devices_active_kind).
    Adding one, or giving it a new code, shows a one-time setup code to type
    into the tablet; only its hash is kept.
    """

    def __init__(
        self,
        *,
        db: Session,
        device_repository: LocationKioskDeviceRepository,
    ):
        self.db = db
        self.device_repository = device_repository

    def list_for_location(
        self,
        *,
        location_id: UUID,
    ) -> list[KioskDeviceResponse]:
        return [
            KioskDeviceResponse.model_validate(device, from_attributes=True)
            for device in self.device_repository.list_for_location(location_id=location_id)
        ]

    def settings(
        self,
        *,
        location_id: UUID,
    ) -> KioskSettingsResponse:
        return KioskSettingsResponse(
            enforce_service_times=self.device_repository.enforces_service_times(location_id=location_id),
        )

    @transactional
    def update_settings(
        self,
        *,
        location_id: UUID,
        body: UpdateKioskSettingsRequest,
    ) -> KioskSettingsResponse:
        self.device_repository.set_enforce_service_times(location_id=location_id, enabled=body.enforce_service_times)
        logger.info(
            "Kiosk settings changed",
            extra={
                "event": "kiosk_settings_updated",
                "result": "success",
                "reason": f"enforce_service_times={body.enforce_service_times}",
            },
        )

        return self.settings(location_id=location_id)

    @transactional
    def create(
        self,
        *,
        location_id: UUID,
        body: CreateKioskDeviceRequest,
    ) -> KioskSetupCodeResponse:
        code, code_hash = _new_code()
        expires_at = datetime.now(timezone.utc) + SETUP_CODE_LIFETIME

        device = self.device_repository.create(
            location_id=location_id,
            kind=body.kind,
            name=body.name,
            setup_secret_hash=code_hash,
            setup_code_expires_at=expires_at,
        )

        self._log("Kiosk added", "kiosk_added", device)

        return self._setup_code(device=device, code=code, expires_at=expires_at)

    @transactional
    def new_setup_code(
        self,
        *,
        id: UUID,
    ) -> KioskSetupCodeResponse:
        device = self._get_active(id=id)
        code, code_hash = _new_code()
        expires_at = datetime.now(timezone.utc) + SETUP_CODE_LIFETIME

        self.device_repository.new_setup_code(
            device=device,
            setup_secret_hash=code_hash,
            setup_code_expires_at=expires_at,
        )

        self._log("Kiosk setup code issued", "kiosk_setup_code", device)

        return self._setup_code(device=device, code=code, expires_at=expires_at)

    @transactional
    def revoke(
        self,
        *,
        id: UUID,
    ) -> KioskDeviceResponse:
        device = self._get_active(id=id)

        self.device_repository.revoke(device=device)

        self._log("Kiosk revoked", "kiosk_revoked", device)

        return KioskDeviceResponse.model_validate(device, from_attributes=True)

    def _get_active(
        self,
        *,
        id: UUID,
    ) -> LocationKioskDevice:
        # RLS: only this location's kiosks are visible.
        device = self.device_repository.get_by_id(id=id)

        if not device or not device.is_active:
            raise KioskDeviceNotFoundError()

        return device

    def _setup_code(
        self,
        *,
        device: LocationKioskDevice,
        code: str,
        expires_at: datetime,
    ) -> KioskSetupCodeResponse:
        return KioskSetupCodeResponse(
            device=KioskDeviceResponse.model_validate(device, from_attributes=True),
            setup_code=code,
            expires_at=expires_at,
        )

    def _log(self, message: str, event: str, device: LocationKioskDevice) -> None:
        logger.info(
            message,
            extra={
                "event": event,
                "result": "success",
                "reason": f"device_id={device.id}; kind={getattr(device.kind, 'value', device.kind)}",
            },
        )
