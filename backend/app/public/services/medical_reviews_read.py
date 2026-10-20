from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.children import ChildProfileNotFoundError
from app.public.repositories.child_medical_state import ChildMedicalStateRepository
from app.public.schemas.medical_reviews import (
    ListMedicalReviewsFilterRequest,
    MedicalReviewResponse,
    MedicalReviewSummaryResponse,
)


class ReadMedicalReviewService:
    """
    The staff review list and one child's review. RLS scopes both to the
    session's location (a family reaching this sees only their own
    children).
    """

    def __init__(
        self,
        *,
        db: Session,
        medical_state_repository: ChildMedicalStateRepository,
    ):
        self.db = db
        self.medical_state_repository = medical_state_repository

    def list_with_filters(
        self,
        *,
        filters: ListMedicalReviewsFilterRequest,
    ) -> list[MedicalReviewSummaryResponse]:
        rows = self.medical_state_repository.list_reviews(
            review_status=filters.review_status,
        )

        return [
            MedicalReviewSummaryResponse.model_validate(row, from_attributes=True)
            for row in rows
        ]

    def get(
        self,
        *,
        child_id: UUID,
    ) -> MedicalReviewResponse:
        row = self.medical_state_repository.get_review(child_id=child_id)

        if not row:
            raise ChildProfileNotFoundError()

        return MedicalReviewResponse.model_validate(row, from_attributes=True)
