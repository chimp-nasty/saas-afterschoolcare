from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.auth import RoleNotFoundError
from app.auth.services.auth import AuthService
from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.role import RoleRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.auth.schemas.auth import RegistrationRequest

class CustomerService:
    def __init__(self, *, db: Session):
        self.db = db

        self.auth = AuthService(db=db)
        self.location_user_roles = LocationUserRoleRepository(db=db)
        self.roles = RoleRepository(db=db)
        self.customer_profiles = CustomerProfileRepository(db=db)

    def onboard(
        self,
        *,
        body: RegistrationRequest,
        location_id: UUID
    ) -> None:
        try:
            user = self.auth.register_user(
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