from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.auth import UserNotFoundError
from app.errors.children import ChildAgeOutOfRangeError
from app.errors.customer import (
    CustomerProfileIncompleteError,
    CustomerProfileNotFoundError,
)

from app.db.models import CustomerProfile, User
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.public.repositories.location_service import LocationServiceRepository
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
        customer_profile_repository: CustomerProfileRepository,
        location_service_repository: LocationServiceRepository,
        user_repository: UserRepository,
    ):
        self.db = db
        self.child_repository = child_repository
        self.customer_profile_repository = customer_profile_repository
        self.location_service_repository = location_service_repository
        self.user_repository = user_repository

    @transactional
    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        body: CreateChildRequest
    ) -> ChildResponse:
        # Validate Profile completeness
        self._validate_customer(user_id=user_id)

        self._validate_age(location_id=location_id, dob=body.dob)

        # Create profile. A duplicate active child is rejected by the
        # database (uq_child_profile_active_identity).
        child = self.child_repository.create(
            location_id=location_id,
            user_id=user_id,

            first_name=body.first_name,
            last_name=body.last_name,
            dob=body.dob,
            medical_info=body.medical_info,
            allergy_info=body.allergy_info,
            medication_info=body.medication_info,
            # Required by the database when the family has other pickup
            # people (trg_child_profile_pickup_consent).
            pickup_consent_confirmed_at=(
                datetime.now(timezone.utc) if body.pickup_consent else None
            ),
        )

        # Its medical review state (pending or not_required) is created by
        # trg_child_profile_medical_review (schema/0004).

        # The account holder is already on the pickup list (their row is
        # kept in sync with their profile, schema/0004), and everyone on it
        # may collect every child.

        self.db.flush()

        return ChildResponse.model_validate(
            self.child_repository.get_with_context_by_id(id=child.id),
            from_attributes=True,
        )

    def _validate_age(
        self,
        *,
        location_id: UUID,
        dob: date,
    ) -> None:
        """
        The child's age today must fit at least one of the location's
        services (the widest range across them). Each booking checks the
        age on its own date against its own service (schema/0009).
        """
        limits = self.location_service_repository.get_child_age_limits(
            location_id=location_id,
        )

        if not limits or limits.min_age is None:
            return

        today = limits.today
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if not limits.min_age <= age <= limits.max_age:
            raise ChildAgeOutOfRangeError(
                min_age=limits.min_age,
                max_age=limits.max_age,
            )

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