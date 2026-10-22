from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints, field_validator, ConfigDict

from app.public.schemas.enums import AustralianState, EmergencyRelation
from app.public.schemas.phone import normalise_au_phone


class UpdateContactDetailsRequest(BaseModel):
    """The parent's phone and address: what an admin may correct (Admin › Families)."""

    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    suburb: str | None = None
    state: AustralianState | None = None
    postcode: str | None = None

    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if len(value) != 4 or not value.isdigit():
            raise ValueError("Postcode must be a 4-digit Australian postcode")

        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return normalise_au_phone(value)


class UpdateCustomerProfileRequest(UpdateContactDetailsRequest):
    """
    The family's own profile: their contact details and their emergency
    contact (only the family sets it; trg_customer_profile_emergency_owner).
    Its phone must be a valid Australian number and not the parent's own
    (ck_customer_profile_emergency_phone_distinct).
    """

    emergency_contact_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: EmergencyRelation | None = None
    # Required when the relation is "other"; cleared when it isn't (the service).
    emergency_contact_relation_other: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return normalise_au_phone(value)


class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    phone: str | None
    address_line_1: str | None
    address_line_2: str | None
    suburb: str | None
    state: AustralianState | None
    postcode: str | None

    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: EmergencyRelation | None
    emergency_contact_relation_other: str | None

    updated_at: datetime


