from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator, ConfigDict

from app.public.schemas.enums import AustralianState


class UpdateCustomerProfileRequest(BaseModel):
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

        value = value.strip()

        digits = (
            value
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        if digits.startswith("+61"):
            digits = "0" + digits[3:]

        if not digits.isdigit() or len(digits) != 10:
            raise ValueError("Enter a valid Australian phone number")

        return digits

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

    updated_at: datetime


