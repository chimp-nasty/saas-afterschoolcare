from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


StaffRole = Literal["staff", "admin"]


class StaffAccountResponse(BaseModel):
    """Someone who works at the location, as its admins see them."""

    user_id: UUID
    first_name: str
    last_name: str
    email: str
    # staff, admin or superadmin (superadmins are shown, not managed here).
    role_code: str
    has_pin: bool
    # None until they first log in (invited).
    last_login: datetime | None


class AddStaffRequest(BaseModel):
    """Add someone to the location's staff; new accounts are emailed an invite."""

    email: EmailStr = Field(max_length=255)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: StaffRole = "staff"

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class AddStaffResponse(BaseModel):
    staff: StaffAccountResponse
    # False: they already had an account (e.g. at another of the business's
    # centres), so no invite was sent; they log in as they already do.
    invited: bool


class RenameStaffRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)


class ChangeStaffRoleRequest(BaseModel):
    role: StaffRole
