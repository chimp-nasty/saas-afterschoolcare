from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.public.models.enums import MedicalReviewStatus


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
    review_status: list[str] | None = None


class CreateChildRequest(BaseModel):
    first_name: str
    last_name: str
    dob: date

    medical_info: str | None
    allergy_info: str | None
    medication_info: str | None