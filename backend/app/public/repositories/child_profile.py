from uuid import UUID
from datetime import date

from sqlalchemy.engine import Row

from app.db.repository import Repository
from sqlalchemy import or_

from app.db.models import ChildMedicalState, ChildProfile, User


class ChildProfileRepository(Repository):
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
        pickup_consent_confirmed_at=None,
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
            pickup_consent_confirmed_at=pickup_consent_confirmed_at,
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

    def update(
        self,
        *,
        child: ChildProfile,
        values: dict,
    ) -> ChildProfile:
        for field, value in values.items():
            setattr(child, field, value)

        self.db.flush()

        return child

    def deactivate(
        self,
        *,
        child: ChildProfile,
    ) -> ChildProfile:
        child.is_active = False

        self.db.flush()

        return child

    def get_by_unique_contraint(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        first_name: str,
        last_name: str,
        dob: date
    ) -> ChildProfile | None:
        return (
            self.db.query(ChildProfile)
            .filter(
                ChildProfile.location_id == location_id,
                ChildProfile.user_id == user_id,
                ChildProfile.first_name == first_name,
                ChildProfile.last_name == last_name,
                ChildProfile.dob == dob,
                ChildProfile.is_active == True
            )
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
                ChildMedicalState.documentation_request,
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

    def search(
        self,
        *,
        location_id: UUID,
        text: str,
        limit: int = 20,
    ) -> list[Row]:
        """Active children at the location whose first or last name starts with `text` (RLS applies)."""
        pattern = text.replace("%", "").replace("_", "") + "%"

        return (
            self.db.query(
                ChildProfile.id.label("child_id"),
                ChildProfile.first_name,
                ChildProfile.last_name,
                ChildProfile.user_id.label("family_user_id"),
                User.first_name.label("family_first_name"),
                User.last_name.label("family_last_name"),
            )
            .join(User, User.id == ChildProfile.user_id)
            .filter(
                ChildProfile.location_id == location_id,
                ChildProfile.is_active.is_(True),
                or_(ChildProfile.first_name.ilike(pattern), ChildProfile.last_name.ilike(pattern)),
            )
            .order_by(ChildProfile.first_name, ChildProfile.last_name)
            .limit(limit)
            .all()
        )
