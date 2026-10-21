import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.user import UserRepository
from app.auth.schemas.account import AccountResponse, AccountRoleResponse, ChangePasswordRequest
from app.core.security import hash_password, verify_password
from app.db.transaction import transactional
from app.errors.auth import CurrentPasswordIncorrectError, JwtInvalidError
from app.integrations.email.messages import PasswordChangedEmail
from app.integrations.email.outbox import EmailOutbox
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.auth")


class AccountService:
    """
    Your own account, for everyone who logs in: staff, admins and
    superadmins in their staff portal, families on their account page
    (docs/portals.md). Read-only apart from changing your password.
    """

    def __init__(
        self,
        *,
        db: Session,
        users: UserRepository,
        location_user_roles: LocationUserRoleRepository,
        locations: LocationRepository,
    ):
        self.db = db
        self.users = users
        self.location_user_roles = location_user_roles
        self.locations = locations
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
