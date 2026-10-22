from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.children import ChildProfileNotFoundError
from app.public.repositories.child_medical_state import ChildMedicalStateRepository
from app.public.schemas.enums import MedicalReviewStatus
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
        # The approved list grows: newest decision first, to find recent ones.
        rows = self.medical_state_repository.list_reviews(
            review_status=filters.review_status,
            text_query=filters.q.strip() if filters.q else None,
            newest_first=set(filters.review_status) == {MedicalReviewStatus.APPROVED},
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
