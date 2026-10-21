from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.public.schemas.enums import MedicalReviewStatus


class ChildResponse(BaseModel):
    id: UUID
    location_id: UUID
    user_id: UUID

    first_name: str
    last_name: str
    dob: date

    medical_info: str | None
    allergy_info: str | None
    medication_info: str | None

    is_active: bool
    review_status: MedicalReviewStatus
    # What the centre asked the family for, while it's outstanding.
    documentation_request: str | None

    created_at: datetime
    updated_at: datetime


class ChildTableResponse(BaseModel):
    id: UUID
    location_id: UUID
    user_id: UUID

    first_name: str
    last_name: str
    dob: date

    is_active: bool
    review_status: MedicalReviewStatus


class ListChildrenFilterRequest(BaseModel):
    is_active: bool | None = None
    review_status: list[MedicalReviewStatus] | None = None


def _blank_to_none(value: str | None) -> str | None:
    """Blank medical text means no details (and no review)."""
    if value is None:
        return None

    value = value.strip()

    return value or None


class CreateChildRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    dob: date

    medical_info: str | None
    allergy_info: str | None
    medication_info: str | None

    # Everyone already on the family's pickup list may collect this child.
    # Required when the list has anyone besides the account holder.
    pickup_consent: bool = False

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("medical_info", "allergy_info", "medication_info")
    @classmethod
    def _medical_blank_to_none(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class UpdateChildRequest(BaseModel):
    """
    What a family can change about a child. Only the fields sent are
    updated. The date of birth isn't editable (staff correct it); changing
    any medical field sends the child back to medical review.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)

    medical_info: str | None = None
    allergy_info: str | None = None
    medication_info: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("medical_info", "allergy_info", "medication_info")
    @classmethod
    def _medical_blank_to_none(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

class ChildSearchResultResponse(BaseModel):
    """A child found by name, with their family (staff finding a family)."""

    child_id: UUID
    first_name: str
    last_name: str
    family_user_id: UUID
    family_first_name: str
    family_last_name: str
