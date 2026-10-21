from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class StaffKioskMemberResponse(BaseModel):
    """A staff member the staff kiosk offers to act as."""

    user_id: UUID
    first_name: str
    last_name: str
    is_admin: bool
    has_pin: bool
    # Only people on shift can act at the staff kiosk.
    on_shift: bool
    shift_started_at: datetime | None
    # A shift left open from an earlier day: they forgot to clock out, and
    # say when they left when they next clock in.
    unclosed_shift_started_at: datetime | None


class StaffKioskVerifyResponse(BaseModel):
    """The PIN is theirs (for a task that starts with a PIN)."""

    user_id: UUID
    first_name: str


class StaffKioskSignRequest(BaseModel):
    """
    Sign a child in or out. `at` is when it happened, for a missed one
    (default now; never in the future). Signing out says how the child
    left: an approved pickup person, a one-off release with the person's
    name and how it was confirmed, or (before school care) sent to school.
    """

    booking_id: UUID
    action: Literal["in", "out"]
    at: datetime | None = None
    collected_by_pickup_person_id: UUID | None = None
    released_to_name: str | None = Field(default=None, max_length=200)
    release_note: str | None = Field(default=None, max_length=1000)
    sent_to_school: bool = False

    @field_validator("released_to_name", "release_note")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @model_validator(mode="after")
    def _release_needs_a_note(self):
        if self.released_to_name and not self.release_note:
            raise ValueError("Note how the release was confirmed (e.g. phoned the account holder)")

        return self


class StaffKioskBulkRequest(BaseModel):
    """
    One action for several children at once, all or nothing: signing in a
    session's arrivals (after school care), sending a before school session
    to school, or signing out brothers and sisters to the same person (an
    approved pickup person, or a one-off release with how it was confirmed).
    `at` as for one child.
    """

    action: Literal["sign_in", "to_school", "sign_out"]
    booking_ids: list[UUID] = Field(min_length=1, max_length=200)
    at: datetime | None = None
    collected_by_pickup_person_id: UUID | None = None
    released_to_name: str | None = Field(default=None, max_length=200)
    release_note: str | None = Field(default=None, max_length=1000)

    @field_validator("released_to_name", "release_note")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @model_validator(mode="after")
    def _release_needs_a_note(self):
        if self.released_to_name and not self.release_note:
            raise ValueError("Note how the release was confirmed (e.g. phoned the account holder)")

        return self


class StaffKioskUndoRequest(BaseModel):
    booking_id: UUID
    step: Literal["sign_in", "sign_out"]


class StaffKioskCheckIdRequest(BaseModel):
    pickup_person_id: UUID
    # True: photo ID was checked (also approves). False: approved without ID.
    id_seen: bool


class StaffKioskShiftRequest(BaseModel):
    action: Literal["start", "end"]
    # Clocking in after forgetting to clock out: when they left that shift.
    previous_shift_ended_at: datetime | None = None
