from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints


# The platform's site (docs/tenant-administration.md, stage 4).

class PlatformSessionResponse(BaseModel):
    platform_admin_id: UUID
    email: str


class PlatformTenantResponse(BaseModel):
    """One business, as the platform sees it: no families, bookings or staff."""

    id: UUID
    name: str
    code: str
    created_at: datetime
    is_active: bool
    # The email it was invited with (its owner's when they registered).
    invited_email: str | None
    location_count: int
    payments_connected: bool
    takes_payments: bool
    # Its live main domain, and how many of its domains are being set up
    # (pending, proven, suspended or failed).
    custom_domain: str | None
    domains_in_progress: int


class SetTenantActiveRequest(BaseModel):
    is_active: bool


class CreateInviteRequest(BaseModel):
    email: EmailStr


class InviteResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    expires_at: datetime


class CreatedInviteResponse(InviteResponse):
    # The one-time link to send: shown once, never stored.
    url: str


class InviteDetailsResponse(BaseModel):
    """What the registration page shows about its invite."""

    email: str


TenantCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9-]*$"),
]


class RegisterTenantRequest(BaseModel):
    """
    A business registering with its invite: its name and web address, and
    its owner (the invite's email). Everything else comes after, in
    Business settings.
    """

    invite: str = Field(min_length=1, max_length=200)
    business_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    code: TenantCode
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    password: str = Field(min_length=8, max_length=128)
    terms_accepted: Literal[True]


class RegisteredTenantResponse(BaseModel):
    # Where the owner logs in: their own site's Business settings.
    business_login_url: str
