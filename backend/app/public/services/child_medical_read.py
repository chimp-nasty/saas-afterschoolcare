from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional

from app.errors.children import ChildProfileNotFoundError
from app.public.repositories.child_document import ChildDocumentRepository
from app.public.repositories.child_medical_state import ChildMedicalStateRepository
from app.public.schemas.child_documents import ChildDocumentResponse
from app.public.schemas.child_medical import ActionPlanResponse, ChildMedicalResponse
from app.public.schemas.enums import ChildDocumentType, MedicalReviewStatus


# A plan uploaded this recently is flagged so the folder copy is replaced,
# even once it's been reviewed.
NEW_PLAN_DAYS = 7


def _value(enum_value) -> str:
    # The database models have their own enum classes; compare by value.
    return getattr(enum_value, "value", enum_value)


class ReadChildMedicalService:
    """
    Children's medical details for the staff caring for them (the staff
    kiosk, on the kiosk channel; docs/portals.md): one child's details and
    documents, and the location's action plans for the physical folder.
    RLS decides who sees them: staff only at the staff kiosk, admins on the
    website. Links to the files come from ReadChildDocumentService.
    """

    def __init__(
        self,
        *,
        db: Session,
        medical_state_repository: ChildMedicalStateRepository,
        document_repository: ChildDocumentRepository,
    ):
        self.db = db
        self.medical_state_repository = medical_state_repository
        self.document_repository = document_repository

    def get(
        self,
        *,
        child_id: UUID,
    ) -> ChildMedicalResponse:
        row = self.medical_state_repository.get_review(child_id=child_id)

        if not row:
            raise ChildProfileNotFoundError()

        return ChildMedicalResponse(
            child_id=row.child_id,
            first_name=row.first_name,
            last_name=row.last_name,
            medical_info=row.medical_info,
            allergy_info=row.allergy_info,
            medication_info=row.medication_info,
            review_status=MedicalReviewStatus(_value(row.review_status)),
            status_since=row.status_since,
            documents=[
                ChildDocumentResponse.model_validate(document, from_attributes=True)
                for document in self.document_repository.list_current_for_child(child_id=child_id)
            ],
        )

    def action_plans(
        self,
        *,
        location_id: UUID,
    ) -> list[ActionPlanResponse]:
        recent = datetime.now(timezone.utc) - timedelta(days=NEW_PLAN_DAYS)
        unreviewed = {MedicalReviewStatus.PENDING, MedicalReviewStatus.DOCUMENTATION_REQUESTED}

        plans = []

        for row in self.document_repository.list_action_plans(location_id=location_id):
            status = MedicalReviewStatus(_value(row.review_status))

            plans.append(ActionPlanResponse(
                child_id=row.child_id,
                child_first_name=row.child_first_name,
                child_last_name=row.child_last_name,
                document_id=row.document_id,
                document_type=ChildDocumentType(_value(row.document_type)),
                uploaded_at=row.uploaded_at,
                review_status=status,
                is_new=status in unreviewed or row.uploaded_at >= recent,
                printed_at=row.printed_at,
                printed_by=row.printed_by,
            ))

        return plans


class ActionPlanPrintService:
    """
    Staff at the staff kiosk confirming they've printed a plan for the
    folder, or correcting it. The database allows it only for staff on
    shift there (public.set_document_printed) and records who.
    """

    def __init__(
        self,
        *,
        db: Session,
        document_repository: ChildDocumentRepository,
    ):
        self.db = db
        self.document_repository = document_repository

    @transactional
    def set_printed(
        self,
        *,
        document_id: UUID,
        printed: bool,
    ) -> None:
        self.document_repository.set_printed(id=document_id, printed=printed)
