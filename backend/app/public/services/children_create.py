from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.auth import UserNotFoundError
from app.errors.customer import (
    CustomerProfileIncompleteError,
    CustomerProfileNotFoundError,
)

from app.auth.models.user import User
from app.public.models.customer_profile import CustomerProfile
from app.public.models.enums import MedicalReviewStatus

from app.public.repositories.child_profile import ChildProfileRepository
from app.public.repositories.child_medical_state import ChildMedicalStateRepository
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.auth.repositories.user import UserRepository

from app.public.schemas.children import (
    ChildResponse,
    CreateChildRequest,
)


class CreateChildService:
    def __init__(
        self,
        *,
        db: Session,
        child_repository: ChildProfileRepository,
        child_medical_state_repository: ChildMedicalStateRepository,
        authorized_pickup_repository: AuthorizedPickupPersonRepository,
        customer_profile_repository: CustomerProfileRepository,
        user_repository: UserRepository,
    ):
        self.db = db
        self.child_repository = child_repository
        self.child_medical_state_repository = child_medical_state_repository
        self.authorized_pickup_repository = authorized_pickup_repository
        self.customer_profile_repository = customer_profile_repository
        self.user_repository = user_repository

    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        body: CreateChildRequest
    ) -> ChildResponse:
        try:
            # Validate Profile completeness
            user, profile = self._validate_customer(user_id=user_id)

            # Create profile
            child = self.child_repository.create(
                location_id=location_id,
                user_id=user_id,

                first_name=body.first_name,
                last_name=body.last_name,
                dob=body.dob,
                medical_info=body.medical_info,
                allergy_info=body.allergy_info,
                medication_info=body.medication_info
            )

            # Create medical state
            review_status = (
                MedicalReviewStatus.PENDING
                if child.medical_info or child.allergy_info or child.medication_info
                else MedicalReviewStatus.NOT_REQUIRED
            )

            self.child_medical_state_repository.create(
                child_id=child.id,
                review_status=review_status
            )

            # Create auth pickup for user
            self.authorized_pickup_repository.create(
                child_id=child.id,
                user_id=user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=profile.phone,
                relation="Guardian",
            )

            self.db.flush()
            self.db.refresh(child)

            result = ChildResponse(
                id=child.id,
                location_id=child.location_id,
                user_id=child.user_id,

                first_name=child.first_name,
                last_name=child.last_name,
                dob=child.dob,

                medical_info=child.medical_info,
                allergy_info=child.allergy_info,
                medication_info=child.medication_info,

                is_active=child.is_active,
                review_status=review_status,

                created_at=child.created_at,
                updated_at=child.updated_at,
            )

            self.db.commit()

            return result

        except Exception:
            self.db.rollback()
            raise

    def _validate_customer(
        self,
        *,
        user_id: UUID
    ) -> tuple[User, CustomerProfile]:
        user = self.user_repository.get_by_id(
            id=user_id
        )

        if not user:
            raise UserNotFoundError()
    
        profile = self.customer_profile_repository.get_by_user_id(
            user_id=user_id
        )

        if not profile:
            raise CustomerProfileNotFoundError()

        missing_fields = self.customer_profile_repository.get_missing_profile_fields(
            profile=profile
        )

        if missing_fields:
            raise CustomerProfileIncompleteError(
                missing_fields=missing_fields
            )

        return user, profile