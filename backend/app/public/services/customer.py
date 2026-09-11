from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.errors.auth import RoleNotFoundError, UserCollisionError
from app.errors.customer import CustomerProfileNotFoundError

from app.auth.repositories.user import UserRepository
from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.role import RoleRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.auth.repositories.rls_context import RlsContextRepository
from app.public.repositories.customer_profile import CustomerProfileRepository

from app.auth.schemas.auth import RegistrationRequest
from app.public.schemas.customer import (
    UpdateCustomerProfileRequest,
    CustomerProfileResponse,
)


class CustomerService:
    def __init__(
        self,
        *,
        db: Session,
        users: UserRepository,
        location_user_roles: LocationUserRoleRepository,
        roles: RoleRepository,
        customer_profiles: CustomerProfileRepository,
        rls_context: RlsContextRepository,
    ):
        self.db = db

        self.users = users
        self.location_user_roles = location_user_roles
        self.roles = roles
        self.customer_profiles = customer_profiles
        self.rls_context = rls_context

    def onboard(
        self,
        *,
        body: RegistrationRequest,
        location_id: UUID
    ) -> None:
        try:
            existing_user = self.users.get_by_email(
                email=body.email
            )

            if existing_user:
                raise UserCollisionError()

            user_id = uuid4()

            self.rls_context.set_user_id(
                user_id=user_id,
            )

            password_hash = hash_password(
                password=body.password
            )

            user = self.users.create(
                id=user_id,
                email=body.email,
                password_hash=password_hash,
                first_name=body.first_name,
                last_name=body.last_name,
                terms_accepted_at=datetime.now(timezone.utc),
            )

            customer_role = self.roles.get_by_code(
                code="customer"
            )

            if not customer_role:
                raise RoleNotFoundError()

            self.location_user_roles.create(
                user_id=user.id,
                location_id=location_id,
                role_id=customer_role.id
            )

            self.customer_profiles.create(
                user_id=user.id
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    def get(
        self,
        *,
        user_id: UUID
    ) -> CustomerProfileResponse:
        profile = self.customer_profiles.get_by_user_id(
            user_id=user_id
        )

        if not profile:
            raise CustomerProfileNotFoundError()

        return CustomerProfileResponse.model_validate(profile)

    def update(
        self,
        *,
        user_id: UUID,
        body: UpdateCustomerProfileRequest,
    ) -> CustomerProfileResponse:
        try:
            profile = self.customer_profiles.get_by_user_id(
                user_id=user_id
            )

            if not profile:
                raise CustomerProfileNotFoundError()

            self.customer_profiles.update(
                profile=profile,
                fields=body.model_dump(exclude_unset=True)
            )

            self.db.flush()
            self.db.refresh(profile)

            result = CustomerProfileResponse.model_validate(profile)

            self.db.commit()

            return result

        except Exception:
            self.db.rollback()
            raise

