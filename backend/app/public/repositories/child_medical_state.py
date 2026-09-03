from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.child_medical_state import ChildMedicalState


class ChildMedicalStateRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        child_id: UUID,
        review_status: str = "not_required",
        updated_at=None,
        updated_by_user_id: UUID | None = None,
    ) -> ChildMedicalState:
        record = ChildMedicalState(
            child_id=child_id,
            review_status=review_status,
            updated_at=updated_at,
            updated_by_user_id=updated_by_user_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildMedicalState | None:
        return (
            self.db.query(ChildMedicalState)
            .filter(ChildMedicalState.child_id == id)
            .first()
        )
