from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.errors.auth import RoleNotFoundError
from app.errors.customer import CustomerProfileNotFoundError
from app.auth.services.auth import AuthService

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
    def __init__(self, *, db: Session):
        self.db = db

        self.auth = AuthService(db=db)
        self.location_user_roles = LocationUserRoleRepository(db=db)
        self.roles = RoleRepository(db=db)
        self.customer_profiles = CustomerProfileRepository(db=db)
        self.rls_context = RlsContextRepository(db=db)

    def onboard(
        self,
        *,
        body: RegistrationRequest,
        location_id: UUID
    ) -> None:
        try:
            user_id = uuid4()

            self.rls_context.set_user_id(
                user_id=user_id,
            )

            user = self.auth.register_user(
                id=user_id,
                body=body
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

