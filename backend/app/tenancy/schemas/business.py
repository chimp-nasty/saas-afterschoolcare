from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator

from app.public.schemas.enums import AustralianState
from app.public.schemas.phone import normalise_au_phone


# Business settings (/business): docs/tenant-administration.md.

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

# A location's code is the first part of its address (/varsity). Some are
# reserved for the site's own pages (ck_locations_code_reserved).
LocationCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9-]*$"),
]

# The zones ck_locations_timezone allows.
AustralianTimezone = Literal[
    "Australia/Brisbane",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Australia/Hobart",
    "Australia/Adelaide",
    "Australia/Darwin",
    "Australia/Perth",
    "Australia/Broken_Hill",
    "Australia/Lord_Howe",
    "Australia/Eucla",
]


def _optional_phone(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None

    return normalise_au_phone(value)


class BusinessSettingsRequest(BaseModel):
    """
    The business's details, all at once (the settings form sends every
    field). The ABN's check digits are the database's (ck_tenants_abn).
    The about text is page text, edited on /about (SiteRequest).
    """

    name: Name
    legal_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    abn: str | None = None
    email: EmailStr | None = None
    phone: str | None = None

    @field_validator("legal_name")
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("abn")
    @classmethod
    def validate_abn(cls, value: str | None) -> str | None:
        if value is None:
            return None

        digits = value.replace(" ", "")

        if not digits:
            return None

        if len(digits) != 11 or not digits.isdigit():
            raise ValueError("An ABN is 11 digits")

        return digits

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return _optional_phone(value)


class BusinessSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    legal_name: str | None
    abn: str | None
    email: str | None
    phone: str | None


class BusinessLocationRequest(BaseModel):
    """
    A location's details, all at once (adding one, or the edit form).
    Changing its code changes its address: old links then lead to the
    landing page, where families choose it again.
    """

    name: Name
    code: LocationCode
    address_line_1: Name
    address_line_2: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    suburb: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    state: AustralianState
    postcode: str
    phone: str | None = None
    email: EmailStr | None = None
    timezone: AustralianTimezone = "Australia/Brisbane"

    @field_validator("address_line_2")
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, value: str) -> str:
        value = value.strip()

        if len(value) != 4 or not value.isdigit():
            raise ValueError("Postcode must be a 4-digit Australian postcode")

        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return _optional_phone(value)


class BusinessLocationResponse(BaseModel):
    id: UUID
    code: str
    name: str
    address_line_1: str
    address_line_2: str | None
    suburb: str
    state: str
    postcode: str
    phone: str | None
    email: str | None
    timezone: str
    # How many of its services families can book (none for a new location
    # until its superadmin sets them up).
    services_offered: int


class BusinessOverviewResponse(BaseModel):
    """The setup checklist on Business settings' first page."""

    name: str
    # Legal name, ABN, email and phone are all filled in.
    details_complete: bool
    locations: list[BusinessLocationResponse]
    payments_connected: bool
    takes_payments: bool
