from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.transaction import transactional
from app.errors.auth import RoleNotFoundError
from app.errors.customer import CustomerProfileNotFoundError
from app.integrations.email.messages import WelcomeEmail
from app.integrations.email.outbox import EmailOutbox

from app.auth.repositories.user import UserRepository
from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.role import RoleRepository
from app.auth.repositories.rls_context import RlsContextRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.tenancy.repositories.tenant_site import TenantSiteRepository
from app.public.schemas.enums import EmergencyRelation

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
        site_repository: TenantSiteRepository,
        rls_context: RlsContextRepository,
    ):
        self.db = db

        self.users = users
        self.location_user_roles = location_user_roles
        self.roles = roles
        self.customer_profiles = customer_profiles
        self.site_repository = site_repository
        self.rls_context = rls_context
        self.emails = EmailOutbox(db)

    @transactional
    def onboard(
        self,
        *,
        body: RegistrationRequest,
        location_id: UUID
    ) -> None:
        user_id = uuid4()

        self.rls_context.set_user_id(
            user_id=user_id,
        )

        password_hash = hash_password(
            password=body.password
        )

        # An existing email is rejected by the database (uq_users_email).
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

        # The business's terms they've just accepted: its current version,
        # kept on record (customer_profile.terms_document_id).
        terms = self.site_repository.current_document_for_location(
            location_id=location_id,
            kind="terms",
        )

        self.customer_profiles.create(
            user_id=user.id,
            terms_document_id=terms.id if terms else None,
        )

        self.emails.queue(WelcomeEmail(
            location_id=location_id,
            user_id=user.id,
            to_email=user.email,
            first_name=user.first_name,
        ))

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

    @transactional
    def update(
        self,
        *,
        user_id: UUID,
        body: UpdateCustomerProfileRequest,
    ) -> CustomerProfileResponse:
        profile = self.customer_profiles.get_by_user_id(
            user_id=user_id
        )

        if not profile:
            raise CustomerProfileNotFoundError()

        fields = body.model_dump(exclude_unset=True)

        # The "other" wording only goes with the "other" relation.
        if fields.get("emergency_contact_relation") not in (None, EmergencyRelation.OTHER):
            fields["emergency_contact_relation_other"] = None

        self.customer_profiles.update(
            profile=profile,
            fields=fields
        )

        self.db.flush()
        self.db.refresh(profile)

        return CustomerProfileResponse.model_validate(profile)
