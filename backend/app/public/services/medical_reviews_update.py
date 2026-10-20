import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.user import UserRepository
from app.db.transaction import transactional
from app.errors.children import ChildProfileInactiveError, ChildProfileNotFoundError
from app.integrations.email.messages import ChildApprovedEmail, DocumentsRequestedEmail
from app.integrations.email.outbox import EmailOutbox
from app.public.repositories.action import ActionRepository
from app.public.repositories.child_medical_state import ChildMedicalStateRepository
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.enums import MedicalReviewDecision
from app.public.schemas.medical_reviews import (
    MedicalReviewDecisionRequest,
    MedicalReviewResponse,
)


logger = logging.getLogger("app.medical")

# The frontend's child page tabs (frontend/src/lib/navigation/tabs.ts).
_CHILD_PROFILE_TAB = "profile"
_CHILD_DOCUMENTS_TAB = "manage-documents"


class UpdateMedicalReviewService:
    """
    Staff deciding a child's medical review: approve (the child can be
    booked), or ask the family for documentation. Which decisions are
    allowed, recording the reviewer and clearing an old request all happen
    in the database (trg_child_medical_state_rules, schema/0004).

    The family is told twice: an action in the app that links to the
    child's page (with the staff message), and an email that only says
    there's something to look at (docs/email-policy.md).
    """

    def __init__(
        self,
        *,
        db: Session,
        medical_state_repository: ChildMedicalStateRepository,
        child_repository: ChildProfileRepository,
        action_repository: ActionRepository,
        user_repository: UserRepository,
    ):
        self.db = db
        self.medical_state_repository = medical_state_repository
        self.child_repository = child_repository
        self.action_repository = action_repository
        self.user_repository = user_repository
        self.emails = EmailOutbox(db)

    @transactional
    def decide(
        self,
        *,
        child_id: UUID,
        body: MedicalReviewDecisionRequest,
        user_id: UUID,
    ) -> MedicalReviewResponse:
        # RLS: staff see their location's children only.
        child = self.child_repository.get_by_id(id=child_id)
        state = self.medical_state_repository.get_by_id(id=child_id)

        if not child or not state:
            raise ChildProfileNotFoundError()

        if not child.is_active:
            raise ChildProfileInactiveError()

        requesting = body.decision == MedicalReviewDecision.DOCUMENTATION_REQUESTED
        already_approved = state.review_status == MedicalReviewDecision.APPROVED

        self.medical_state_repository.decide(
            state=state,
            review_status=body.decision,
            documentation_request=body.message if requesting else None,
        )

        # Staff outrank the family, so RLS lets them read the account holder.
        family = self.user_repository.get_by_id(id=child.user_id)
        recipient = dict(
            location_id=child.location_id,
            user_id=family.id,
            to_email=family.email,
            first_name=family.first_name,
        )

        if requesting:
            self.action_repository.create(
                user_id=child.user_id,
                location_id=child.location_id,
                child_id=child.id,
                created_by_user_id=user_id,
                target=_CHILD_DOCUMENTS_TAB,
                title=f"Documents needed for {child.first_name}",
                message=body.message,
            )
            self.emails.queue(DocumentsRequestedEmail(
                **recipient,
                child_id=child.id,
                child_first_name=child.first_name,
            ))
        # Approving again changes nothing, so there's nothing to tell.
        elif not already_approved:
            self.action_repository.create(
                user_id=child.user_id,
                location_id=child.location_id,
                child_id=child.id,
                created_by_user_id=user_id,
                target=_CHILD_PROFILE_TAB,
                title=f"{child.first_name} is cleared for bookings",
                message=f"The centre has reviewed {child.first_name}'s medical details. You can now book sessions.",
            )
            self.emails.queue(ChildApprovedEmail(
                **recipient,
                child_first_name=child.first_name,
            ))

        logger.info(
            "Medical review decided",
            extra={
                "event": "medical_review_decided",
                "result": "success",
                "reason": f"child_id={child_id}; decision={body.decision}",
            },
        )

        return MedicalReviewResponse.model_validate(
            self.medical_state_repository.get_review(child_id=child_id),
            from_attributes=True,
        )
