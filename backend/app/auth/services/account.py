import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.user import UserRepository
from app.auth.schemas.account import (
    AccountResponse,
    AccountRoleResponse,
    ChangePasswordRequest,
    DeactivateAccountRequest,
)
from app.core.security import hash_password, verify_password
from app.db.transaction import transactional
from app.errors.auth import CurrentPasswordIncorrectError, JwtInvalidError
from app.errors.customer import AccountNotDeactivatedError
from app.integrations.email.messages import PasswordChangedEmail
from app.integrations.email.outbox import EmailOutbox
from app.public.repositories.family_deactivation import FamilyDeactivationRepository
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.auth")


class AccountService:
    """
    Your own account, for everyone who logs in: staff, admins and
    superadmins in their staff portal, families on their account page
    (docs/portals.md). Read-only apart from changing your password, and
    for families, deactivating it and asking to be reactivated
    (docs/account-deactivation.md).
    """

    def __init__(
        self,
        *,
        db: Session,
        users: UserRepository,
        location_user_roles: LocationUserRoleRepository,
        locations: LocationRepository,
        deactivations: FamilyDeactivationRepository,
    ):
        self.db = db
        self.users = users
        self.location_user_roles = location_user_roles
        self.locations = locations
        self.deactivations = deactivations
        self.emails = EmailOutbox(db)

    def get(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> AccountResponse:
        # RLS: a user always sees their own row.
        user = self.users.get_by_id(id=user_id)
        location = self.locations.get_by_id(id=location_id)

        if not user or not location:
            raise JwtInvalidError()

        # Only this tenant's locations: another business you also use isn't
        # this one's to show.
        roles = self.location_user_roles.list_with_locations(user_id=user_id, tenant_id=location.tenant_id)

        return AccountResponse(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=[
                AccountRoleResponse(
                    location_code=role_location.code,
                    location_name=role_location.name,
                    role_code=role.code,
                    role_name=role.name,
                )
                for role_location, role in roles
            ],
        )

    @transactional
    def change_password(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        body: ChangePasswordRequest,
    ) -> None:
        """
        Change your password, after re-entering the current one (so nobody
        at a logged-in browser can take the account over). The "password
        changed" email goes out from this location.
        """
        user = self.users.get_by_id(id=user_id)

        if not user or not verify_password(password=body.current_password, hashed_password=user.password_hash):
            raise CurrentPasswordIncorrectError()

        self.users.update_password_hash(user=user, password_hash=hash_password(password=body.new_password))

        self.emails.queue(PasswordChangedEmail(
            location_id=location_id,
            user_id=user.id,
            to_email=user.email,
            first_name=user.first_name,
        ))

        logger.info(
            "Password changed",
            extra={"event": "password_changed", "result": "success", "reason": f"user_id={user.id}"},
        )

    @transactional
    def deactivate(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        body: DeactivateAccountRequest,
    ) -> None:
        """
        Deactivate your family account at this centre, after re-entering your
        password. The database refuses someone who also works here, and a
        family with upcoming bookings; nothing is deleted.
        """
        user = self.users.get_by_id(id=user_id)

        if not user or not verify_password(password=body.password, hashed_password=user.password_hash):
            raise CurrentPasswordIncorrectError()

        self.deactivations.create(user_id=user_id, location_id=location_id)

        logger.info(
            "Family deactivated their account",
            extra={"event": "account_deactivated", "result": "success", "reason": f"user_id={user_id}"},
        )

    @transactional
    def request_reactivation(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        """Ask the centre's admins to reactivate you (asking again changes nothing)."""
        deactivation = self.deactivations.get(user_id=user_id, location_id=location_id)

        if not deactivation:
            raise AccountNotDeactivatedError()

        if deactivation.reactivation_requested_at is not None:
            return

        self.deactivations.request_reactivation(user_id=user_id, location_id=location_id)

        logger.info(
            "Family asked to be reactivated",
            extra={"event": "reactivation_requested", "result": "success", "reason": f"user_id={user_id}"},
        )
