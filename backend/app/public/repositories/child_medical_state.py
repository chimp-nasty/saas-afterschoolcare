from uuid import UUID

from sqlalchemy import func
from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import (
    ChildDocument,
    ChildMedicalState,
    ChildProfile,
    CustomerProfile,
    User,
)
from app.public.schemas.enums import ChildDocumentUploadStatus, MedicalReviewStatus


class ChildMedicalStateRepository(Repository):
    def create(
        self,
        *,
        child_id: UUID,
        review_status: MedicalReviewStatus = MedicalReviewStatus.NOT_REQUIRED,
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

    def decide(
        self,
        *,
        state: ChildMedicalState,
        review_status: str,
        documentation_request: str | None,
    ) -> ChildMedicalState:
        """
        Record a staff decision. trg_child_medical_state_rules (schema/0004)
        checks it, records the reviewer and clears the request on approval.
        """
        state.review_status = review_status
        state.documentation_request = documentation_request

        self.db.flush()

        return state

    def get_review(
        self,
        *,
        child_id: UUID,
    ) -> Row | None:
        return (
            self._review_query(
                ChildProfile.is_active,
                ChildProfile.medical_info,
                ChildProfile.allergy_info,
                ChildProfile.medication_info,
                ChildMedicalState.updated_by_user_id.label("reviewed_by_user_id"),
                User.id.label("family_user_id"),
                User.email.label("family_email"),
            )
            .filter(ChildProfile.id == child_id)
            .first()
        )

    def list_reviews(
        self,
        *,
        review_status: list[str],
    ) -> list[Row]:
        """Current children in the given statuses, longest waiting first."""
        document_count = (
            self.db.query(func.count(ChildDocument.id))
            .filter(
                ChildDocument.child_id == ChildProfile.id,
                ChildDocument.is_active.is_(True),
                ChildDocument.upload_status == ChildDocumentUploadStatus.UPLOADED,
            )
            .correlate(ChildProfile)
            .scalar_subquery()
        )

        return (
            self._review_query(
                document_count.label("document_count"),
            )
            .filter(
                ChildProfile.is_active.is_(True),
                ChildMedicalState.review_status.in_(review_status),
            )
            .order_by(
                "status_since",
                ChildProfile.first_name,
                ChildProfile.last_name,
            )
            .all()
        )

    def _review_query(self, *columns):
        # A new child's state has no updated_at until it first changes.
        status_since = func.coalesce(
            ChildMedicalState.updated_at,
            ChildProfile.created_at,
        )

        return (
            self.db.query(
                ChildProfile.id.label("child_id"),
                ChildProfile.first_name,
                ChildProfile.last_name,
                ChildProfile.dob,
                ChildMedicalState.review_status,
                ChildMedicalState.documentation_request,
                status_since.label("status_since"),
                User.first_name.label("family_first_name"),
                User.last_name.label("family_last_name"),
                CustomerProfile.phone.label("family_phone"),
                *columns,
            )
            .join(
                ChildMedicalState,
                ChildMedicalState.child_id == ChildProfile.id,
            )
            .join(
                User,
                User.id == ChildProfile.user_id,
            )
            .outerjoin(
                CustomerProfile,
                CustomerProfile.user_id == ChildProfile.user_id,
            )
        )
