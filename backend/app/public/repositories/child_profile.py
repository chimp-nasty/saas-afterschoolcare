from uuid import UUID

from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.public.models.child_profile import ChildProfile
from app.public.models.child_medical_state import ChildMedicalState


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

    def get_with_context_by_id(
        self,
        *,
        id: UUID,
    ) -> Row | None:
        return (
            self.db.query(
                ChildProfile.id,
                ChildProfile.location_id,
                ChildProfile.user_id,
                ChildProfile.first_name,
                ChildProfile.last_name,
                ChildProfile.dob,
                ChildProfile.medical_info,
                ChildProfile.allergy_info,
                ChildProfile.medication_info,
                ChildProfile.is_active,
                ChildProfile.created_at,
                ChildProfile.updated_at,

                ChildMedicalState.review_status,
            )
            .join(
                ChildMedicalState,
                ChildMedicalState.child_id == ChildProfile.id,
            )
            .filter(
                ChildProfile.id == id,
            )
            .first()
        )

    def list_context_with_filters(
        self,
        *,
        is_active: bool | None = None,
        review_status: list[str] | None = None,
    ) -> list[Row]:
        query = (
            self.db.query(
                ChildProfile.id,
                ChildProfile.location_id,
                ChildProfile.user_id,
                ChildProfile.first_name,
                ChildProfile.last_name,
                ChildProfile.dob,
                ChildProfile.is_active,

                ChildMedicalState.review_status,
            )
            .join(
                ChildMedicalState,
                ChildMedicalState.child_id == ChildProfile.id,
            )
        )

        if is_active is not None:
            query = query.filter(
                ChildProfile.is_active == is_active
            )

        if review_status:
            query = query.filter(
                ChildMedicalState.review_status.in_(
                    review_status
                )
            )

        return (
            query
            .order_by(
                ChildProfile.first_name,
                ChildProfile.last_name,
            )
            .all()
        )