from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Cookie, Depends, Header, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.permission import PermissionRepository
from app.auth.repositories.rls_context import RlsContextRepository
from app.core.config import settings
from app.dependencies.auth import resolve_location_id
from app.dependencies.db import get_db
from app.errors.auth import PermissionNotFoundError
from app.errors.database import map_integrity_error
from app.errors.kiosk import (
    StaffKioskNotOnShiftError,
    KioskNotPairedError,
    KioskPinChangeRequiredError,
    KioskSessionExpiredError,
    KioskWrongKindError,
    StaffKioskLoginInvalidError,
    StaffKioskNoPinError,
    StaffKioskPinLockedError,
    StaffKioskPinRequiredError,
)
from app.kiosk.repositories.kiosk import KioskRepository
from app.kiosk.repositories.staff_kiosk import StaffKioskRepository
from app.public.repositories.staff_shift import StaffShiftRepository
from app.kiosk.tokens import (
    DEVICE_COOKIE,
    DEVICE_LIFETIME,
    DEVICE_RENEW_AFTER,
    SESSION_HEADER,
    SessionKind,
    issue_device_token,
    read_device_token,
    read_session_token,
)


@dataclass(frozen=True)
class KioskDevice:
    device_id: UUID
    location_id: UUID
    kind: str


@dataclass(frozen=True)
class KioskSession:
    device: KioskDevice
    # The pickup person (family kiosk) or staff member (staff kiosk).
    subject_id: UUID
    pin_change_required: bool


def set_device_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=DEVICE_COOKIE,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=int(DEVICE_LIFETIME.total_seconds()),
    )


def require_kiosk_device(kind: SessionKind):
    """
    The paired tablet making the request: its cookie must be current (the
    device active, its token_version unchanged), for the location in the
    URL, and of this kind. A cookie older than 30 days is renewed.
    """

    def dependency(
        response: Response,
        location_id: UUID = Depends(resolve_location_id),
        kiosk_device: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
    ) -> KioskDevice:
        claims = read_device_token(kiosk_device)

        if not claims:
            raise KioskNotPairedError()

        row = KioskRepository(db=db).device(
            device_id=claims.device_id,
            token_version=claims.token_version,
        )
        # kiosk_device() records when the tablet was last used.
        db.commit()

        if not row or row.location_id != location_id:
            raise KioskNotPairedError()

        if row.kind != kind:
            raise KioskWrongKindError()

        if datetime.now(timezone.utc) - claims.issued_at > DEVICE_RENEW_AFTER:
            set_device_cookie(
                response,
                issue_device_token(
                    device_id=claims.device_id,
                    location_id=location_id,
                    kind=row.kind,
                    token_version=claims.token_version,
                ),
            )

        return KioskDevice(device_id=claims.device_id, location_id=location_id, kind=row.kind)

    return dependency


def require_kiosk_session(kind: SessionKind, *, allow_pin_change: bool = False):
    """
    The person using the tablet now: a session token from their login on
    this same device, not expired (60 seconds idle). While their PIN must be
    changed, only the PIN endpoint accepts it.
    """

    def dependency(
        device: KioskDevice = Depends(require_kiosk_device(kind)),
        token: str | None = Header(default=None, alias=SESSION_HEADER),
    ) -> KioskSession:
        claims = read_session_token(token)

        if (
            not claims
            or claims.kind != kind
            or claims.device_id != device.device_id
            or claims.location_id != device.location_id
        ):
            raise KioskSessionExpiredError()

        if claims.pin_change_required and not allow_pin_change:
            raise KioskPinChangeRequiredError()

        return KioskSession(
            device=device,
            subject_id=claims.subject_id,
            pin_change_required=claims.pin_change_required,
        )

    return dependency


# The staff member doing one staff kiosk action, and their PIN for it
# (docs/portals.md: nobody is logged in at the staff kiosk; every action
# carries the PIN). Sent as headers so reads (GET) carry them too.
STAFF_HEADER = "X-Kiosk-Staff"
PIN_HEADER = "X-Kiosk-Pin"

_PIN_ERRORS = {
    "invalid": StaffKioskLoginInvalidError,
    "locked": StaffKioskPinLockedError,
    "no_pin": StaffKioskNoPinError,
}


@dataclass(frozen=True)
class KioskStaff:
    device: KioskDevice
    user_id: UUID


def require_kiosk_staff(*, resource: str, action: str, on_shift: bool = True):
    """
    One action at the staff kiosk, by the staff member whose PIN came with
    it:

    1. the device is this location's paired staff kiosk
    2. the PIN is theirs (a wrong one counts towards the lock)
    3. they're on shift here (public.staff_on_shift), unless this is
       clocking in or out itself (on_shift=False)
    4. their role has this permission on the kiosk channel
    5. the request's database session runs as them, at this location, on
       the kiosk channel, so the normal services, RLS and triggers apply
       and every change is recorded against them and this device

    Nothing is kept afterwards: the next action asks for the PIN again.
    """

    def dependency(
        device: KioskDevice = Depends(require_kiosk_device("staff")),
        staff_id: UUID | None = Header(default=None, alias=STAFF_HEADER),
        pin: str | None = Header(default=None, alias=PIN_HEADER),
        db: Session = Depends(get_db),
    ) -> KioskStaff:
        if staff_id is None or not pin:
            raise StaffKioskPinRequiredError()

        try:
            result = StaffKioskRepository(db=db).verify_pin(
                location_id=device.location_id,
                device_id=device.device_id,
                user_id=staff_id,
                pin=pin,
            )
            # A wrong PIN still counts towards the lock.
            db.commit()
        except IntegrityError as exc:
            # Not staff at this location (staff_kiosk_verify_pin).
            db.rollback()
            raise map_integrity_error(exc) from exc

        if result != "ok":
            raise _PIN_ERRORS[result]()

        if on_shift and not StaffShiftRepository(db=db).is_on_shift(location_id=device.location_id, user_id=staff_id):
            raise StaffKioskNotOnShiftError()

        role_ids = [
            role.role_id
            for role in LocationUserRoleRepository(db=db).list_roles_by_user_and_location(
                user_id=staff_id,
                location_id=device.location_id,
            )
        ]
        granted = PermissionRepository(db=db).list_by_role_ids(role_ids, channel="kiosk")

        if not any(p.resource == resource and p.action == action for p in granted):
            raise PermissionNotFoundError()

        rls = RlsContextRepository(db=db)
        rls.set_user_id(user_id=staff_id)
        rls.set_location_id(location_id=device.location_id)
        rls.set_kiosk_channel(device_id=device.device_id)

        return KioskStaff(device=device, user_id=staff_id)

    return dependency
