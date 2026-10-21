from datetime import datetime

from pydantic import BaseModel, Field


class StaffPinStatusResponse(BaseModel):
    """Whether you have a staff kiosk PIN. The PIN itself is never shown."""

    is_set: bool
    set_at: datetime | None
    # Locked after 5 wrong PINs at the staff kiosk; setting a new one unlocks it.
    is_locked: bool


class SetStaffPinRequest(BaseModel):
    """Your account password (to confirm it's you), and the new 4-digit PIN."""

    password: str = Field(min_length=1, max_length=128)
    pin: str = Field(min_length=4, max_length=4)
