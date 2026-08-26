from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.child_profile import ChildProfile


class ChildProfileRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        first_name: str,
        last_name: str,
        dob: date,
        has_medical_condition: bool = False,
        medical_info: str | None = None,
        has_allergies: bool = False,
        allergy_info: str | None = None,
        requires_medication: bool = False,
        medication_info: str | None = None,
        medical_documentation_provided: bool = False,
        medical_review_required: bool = False,
        medical_review_status_id: int | None = None,
        care_details_confirmed_at: datetime | None = None,
        is_active: bool = True,
    ) -> ChildProfile:
        record = ChildProfile(
            user_id=user_id,
            location_id=location_id,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            has_medical_condition=has_medical_condition,
            medical_info=medical_info,
            has_allergies=has_allergies,
            allergy_info=allergy_info,
            requires_medication=requires_medication,
            medication_info=medication_info,
            medical_documentation_provided=medical_documentation_provided,
            medical_review_required=medical_review_required,
            medical_review_status_id=medical_review_status_id,
            care_details_confirmed_at=care_details_confirmed_at,
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
