from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.child_medical_review import ChildMedicalReview


class ChildMedicalReviewRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        child_id: UUID,
        reviewed_by_user_id: UUID,
        note: str | None = None,
    ) -> ChildMedicalReview:
        record = ChildMedicalReview(
            child_id=child_id,
            reviewed_by_user_id=reviewed_by_user_id,
            note=note,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildMedicalReview | None:
        return (
            self.db.query(ChildMedicalReview)
            .filter(ChildMedicalReview.id == id)
            .first()
        )
