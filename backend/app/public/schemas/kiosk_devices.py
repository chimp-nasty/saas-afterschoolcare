from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


KioskKind = Literal["family", "staff"]


class KioskDeviceResponse(BaseModel):
    id: UUID
    kind: KioskKind
    name: str
    is_active: bool
    # Set once a tablet has been paired with the current code.
    paired_at: datetime | None
    last_used: datetime | None
    # While a setup code is waiting to be used.
    setup_code_expires_at: datetime | None
    created_at: datetime


class CreateKioskDeviceRequest(BaseModel):
    kind: KioskKind
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class KioskSetupCodeResponse(BaseModel):
    """
    Type this code into the tablet at /{location}/kiosk before it expires.
    It's shown once and can only be used once.
    """

    device: KioskDeviceResponse
    setup_code: str
    expires_at: datetime


class KioskSettingsResponse(BaseModel):
    # Children are signed in and out (at either kiosk) only from 2 hours
    # before each session to 2 hours after it.
    enforce_service_times: bool


class UpdateKioskSettingsRequest(BaseModel):
    enforce_service_times: bool
