from sqlalchemy.orm import Session

from app.public.models.medical_review_status import MedicalReviewStatus


class MedicalReviewStatusRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        code: str,
        label: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> MedicalReviewStatus:
        record = MedicalReviewStatus(
            code=code,
            label=label,
            description=description,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: int,
    ) -> MedicalReviewStatus | None:
        return (
            self.db.query(MedicalReviewStatus)
            .filter(MedicalReviewStatus.id == id)
            .first()
        )
