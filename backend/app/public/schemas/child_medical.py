from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.public.schemas.child_documents import ChildDocumentResponse
from app.public.schemas.enums import ChildDocumentType, MedicalReviewStatus


class ChildMedicalResponse(BaseModel):
    """
    A child's medical details for the staff caring for them: what the family
    entered, where the admin review is up to, and their documents. Shown
    when approved, and while awaiting re-review (marked as not yet reviewed).
    """

    child_id: UUID
    first_name: str
    last_name: str

    medical_info: str | None
    allergy_info: str | None
    medication_info: str | None

    review_status: MedicalReviewStatus
    # When it was approved, or when it went back into review.
    status_since: datetime

    documents: list[ChildDocumentResponse]


class ActionPlanResponse(BaseModel):
    """One child's action plan, for the physical folder at the centre."""

    child_id: UUID
    child_first_name: str
    child_last_name: str

    document_id: UUID
    document_type: ChildDocumentType
    uploaded_at: datetime

    review_status: MedicalReviewStatus
    # Replace the folder copy: not yet reviewed by an admin, or uploaded in
    # the last 7 days.
    is_new: bool

    # Staff confirmed they printed it for the folder, and who ("Sam L.").
    printed_at: datetime | None
    printed_by: str | None


class SetPrintedRequest(BaseModel):
    printed: bool
