"""
The kiosk's two credentials (docs: the kiosk design in slice 4):

* the device token: which tablet this is (device, location, kind, and the
  token_version it was paired at). Held in the httpOnly `kiosk_device`
  cookie for a year, renewed as it's used; revoking or re-pairing the
  device (token_version + 1) ends it.
* the session token: who is using the tablet right now (a pickup person
  at the family kiosk, a staff member at the staff kiosk). Held only in the
  kiosk page's memory and sent as a header; it lasts 60 seconds and every
  response hands back a fresh one, so it ends after 60 seconds idle.

Both are signed like the app's access tokens but with their own audience,
so neither can be used as the other, or as a login.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from jwt import InvalidTokenError, decode, encode

from app.core.config import settings


DEVICE_COOKIE = "kiosk_device"
DEVICE_LIFETIME = timedelta(days=365)
# A device cookie older than this is re-issued on its next use.
DEVICE_RENEW_AFTER = timedelta(days=30)

SESSION_HEADER = "X-Kiosk-Session"
SESSION_IDLE = timedelta(seconds=60)

_DEVICE_AUDIENCE = "kiosk-device"
_SESSION_AUDIENCE = "kiosk-session"

SessionKind = Literal["family", "staff"]


@dataclass(frozen=True)
class DeviceClaims:
    device_id: UUID
    location_id: UUID
    kind: str
    token_version: int
    issued_at: datetime


@dataclass(frozen=True)
class SessionClaims:
    kind: SessionKind
    device_id: UUID
    location_id: UUID
    # The pickup person (family kiosk) or staff member (staff kiosk).
    subject_id: UUID
    pin_change_required: bool


def _encode(payload: dict[str, Any], *, audience: str, lifetime: timedelta) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + lifetime

    token = encode(
        {
            **payload,
            "iss": settings.JWT_ISSUER,
            "aud": audience,
            "iat": now,
            "nbf": now,
            "exp": expires_at,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token, expires_at


def _decode(token: str, *, audience: str) -> dict[str, Any] | None:
    try:
        return decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=audience,
            leeway=settings.JWT_CLOCK_SKEW_SECONDS,
        )
    except InvalidTokenError:
        return None


def issue_device_token(*, device_id: UUID, location_id: UUID, kind: str, token_version: int) -> str:
    token, _ = _encode(
        {
            "device_id": str(device_id),
            "location_id": str(location_id),
            "kind": getattr(kind, "value", kind),
            "token_version": token_version,
        },
        audience=_DEVICE_AUDIENCE,
        lifetime=DEVICE_LIFETIME,
    )

    return token


def read_device_token(token: str | None) -> DeviceClaims | None:
    claims = _decode(token, audience=_DEVICE_AUDIENCE) if token else None

    if not claims:
        return None

    try:
        return DeviceClaims(
            device_id=UUID(claims["device_id"]),
            location_id=UUID(claims["location_id"]),
            kind=claims["kind"],
            token_version=int(claims["token_version"]),
            issued_at=datetime.fromtimestamp(claims["iat"], timezone.utc),
        )
    except (KeyError, ValueError, TypeError):
        return None


def issue_session_token(
    *,
    kind: SessionKind,
    device_id: UUID,
    location_id: UUID,
    subject_id: UUID,
    pin_change_required: bool = False,
) -> tuple[str, datetime]:
    """A session token and when it expires (60 seconds from now)."""
    return _encode(
        {
            "kind": kind,
            "device_id": str(device_id),
            "location_id": str(location_id),
            "subject_id": str(subject_id),
            "pin_change_required": pin_change_required,
        },
        audience=_SESSION_AUDIENCE,
        lifetime=SESSION_IDLE,
    )


def read_session_token(token: str | None) -> SessionClaims | None:
    claims = _decode(token, audience=_SESSION_AUDIENCE) if token else None

    if not claims:
        return None

    try:
        return SessionClaims(
            kind=claims["kind"],
            device_id=UUID(claims["device_id"]),
            location_id=UUID(claims["location_id"]),
            subject_id=UUID(claims["subject_id"]),
            pin_change_required=bool(claims["pin_change_required"]),
        )
    except (KeyError, ValueError, TypeError):
        return None
