from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.public.schemas.enums import MedicalReviewDecision, MedicalReviewStatus


class MedicalReviewSummaryResponse(BaseModel):
    """A child in the staff review list."""

    child_id: UUID
    first_name: str
    last_name: str
    dob: date

    review_status: MedicalReviewStatus
    documentation_request: str | None
    # When the child reached this status (added, details changed, or
    # staff's latest decision).
    status_since: datetime
    # Who made the latest decision, as "Sam L."; None while waiting.
    reviewed_by: str | None

    family_first_name: str
    family_last_name: str
    family_phone: str | None

    # Current documents only (uploaded and not removed).
    document_count: int


class MedicalReviewResponse(BaseModel):
    """Everything staff need to review one child, apart from the documents."""

    child_id: UUID
    first_name: str
    last_name: str
    dob: date
    is_active: bool

    medical_info: str | None
    allergy_info: str | None
    medication_info: str | None

    review_status: MedicalReviewStatus
    documentation_request: str | None
    status_since: datetime
    # The staff member behind the latest decision; None while waiting.
    reviewed_by_user_id: UUID | None
    reviewed_by: str | None
    # Confirmed bookings from today on: a reopen or a request leaves them.
    upcoming_bookings: int

    family_user_id: UUID
    family_first_name: str
    family_last_name: str
    family_email: str
    family_phone: str | None


class ListMedicalReviewsFilterRequest(BaseModel):
    # Children waiting on staff or on their family by default.
    review_status: list[MedicalReviewStatus] = Field(
        default_factory=lambda: [
            MedicalReviewStatus.PENDING,
            MedicalReviewStatus.DOCUMENTATION_REQUESTED,
        ]
    )
    # The start of the child's or the parent's name (any word, or the full name).
    q: str | None = Field(default=None, min_length=2, max_length=100)


class MedicalReviewDecisionRequest(BaseModel):
    """
    Approve the child, ask the family for documentation, or reopen an
    approved child for review. A request needs a message saying what's
    needed; it's shown to the family. A reopen always sends the family a
    message in their account; this one, or a default saying staff are
    reviewing.
    """

    decision: MedicalReviewDecision
    message: str | None = Field(default=None, max_length=1000)

    @field_validator("message")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None
