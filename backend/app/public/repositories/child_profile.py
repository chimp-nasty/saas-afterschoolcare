from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.child_profile import ChildProfile


class ChildProfileRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        first_name: str,
        last_name: str,
        dob,
        medical_info: str | None = None,
        allergy_info: str | None = None,
        medication_info: str | None = None,
        is_active: bool = True,
    ) -> ChildProfile:
        record = ChildProfile(
            location_id=location_id,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            medical_info=medical_info,
            allergy_info=allergy_info,
            medication_info=medication_info,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildProfile | None:
        return (
            self.db.query(ChildProfile)
            .filter(ChildProfile.id == id)
            .first()
        )
