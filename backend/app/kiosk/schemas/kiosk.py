from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# A 4-digit PIN, as typed on the kiosk's keypad.
Pin = str


class KioskPairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20)

    @field_validator("code")
    @classmethod
    def _normalise(cls, value: str) -> str:
        # Codes are uppercase; accept them however they're typed.
        return value.strip().upper()


class KioskServiceTodayResponse(BaseModel):
    """One of the centre's sessions today, for the family kiosk's welcome screen."""

    service_name: str
    start_time: time
    end_time: time
    # When signing in and out opens and closes (None: any time today).
    signing_opens_at: datetime | None
    signing_closes_at: datetime | None


class KioskInfoResponse(BaseModel):
    """
    What a paired tablet is: which kind, at which centre, and (the family
    kiosk's welcome screen) the centre's sessions today.
    """

    kind: Literal["family", "staff"]
    location_name: str
    # Family kiosk only (the staff kiosk has its roll).
    sessions_today: list[KioskServiceTodayResponse] = []


class KioskSessionResponse(BaseModel):
    """
    The session token for the person now using the kiosk: send it as the
    X-Kiosk-Session header. It expires at `expires_at` (60 seconds); every
    response that uses it returns a fresh one.
    """

    token: str
    expires_at: datetime


class KioskLoginRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    pin: Pin = Field(min_length=4, max_length=4)


class KioskLoginResponse(BaseModel):
    session: KioskSessionResponse
    first_name: str
    # Choose a new PIN (POST /pin) before anything else.
    pin_change_required: bool


class KioskChangePinRequest(BaseModel):
    new_pin: Pin = Field(min_length=4, max_length=4)


class KioskForgotPinRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class KioskBookingResponse(BaseModel):
    """One of today's sessions for a child the person may collect."""

    booking_id: UUID
    child_first_name: str
    child_last_initial: str
    service_name: str
    start_time: time
    end_time: time
    signed_in_at: datetime | None
    signed_out_at: datetime | None
    # This person is approved to collect (sign out) children.
    can_collect: bool
    # When signing in and out opens and closes here (None: any time today).
    signing_opens_at: datetime | None
    signing_closes_at: datetime | None


class KioskTodayResponse(BaseModel):
    session: KioskSessionResponse
    bookings: list[KioskBookingResponse]


class KioskSignRequest(BaseModel):
    booking_id: UUID
    action: Literal["in", "out"]


class KioskSignResponse(BaseModel):
    session: KioskSessionResponse
    booking_id: UUID
    signed_in_at: datetime | None
    signed_out_at: datetime | None
