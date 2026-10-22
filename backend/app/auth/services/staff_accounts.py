import logging
import uuid
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.password_reset_token import PasswordResetTokenRepository
from app.auth.repositories.rls_context import RlsContextRepository
from app.auth.repositories.role import RoleRepository
from app.auth.repositories.staff_account import StaffAccountRepository
from app.auth.repositories.user import UserRepository
from app.auth.schemas.staff_accounts import (
    AddStaffRequest,
    AddStaffResponse,
    ChangeStaffRoleRequest,
    RenameStaffRequest,
    StaffAccountResponse,
)
from app.core.security import hash_password, hash_token
from app.db.transaction import transactional
from app.errors.auth import (
    PermissionNotFoundError,
    StaffAlreadyActiveError,
    StaffAlreadyHereError,
    StaffIsFamilyHereError,
    StaffNotFoundError,
)
from app.integrations.email.messages import StaffInviteEmail
from app.integrations.email.outbox import EmailOutbox


logger = logging.getLogger("app.auth")

# How long an invite link works (a password reset link: 30 minutes).
INVITE_LIFETIME = timedelta(days=7)


class StaffAccountService:
    """
    Admin › Staff (slice 4-3): a location's staff accounts. Admins and
    superadmins see the list, add staff, resend invites, correct names and
    reset staff PINs; superadmins also make or unmake admins and remove
    people (permissions staff_accounts and staff_admin_roles). The database
    keeps the location safe whoever does it (schema/0004, STAFF ACCOUNTS).

    A new account gets an invite: a single-use link to set their password,
    the password reset link with a 7-day life. Someone who already has an
    account (e.g. at another of the business's centres) is just added.
    """

    def __init__(
        self,
        *,
        db: Session,
        staff_accounts: StaffAccountRepository,
        users: UserRepository,
        roles: RoleRepository,
        location_user_roles: LocationUserRoleRepository,
        password_reset_tokens: PasswordResetTokenRepository,
        rls_context: RlsContextRepository,
    ):
        self.db = db
        self.staff_accounts = staff_accounts
        self.users = users
        self.roles = roles
        self.location_user_roles = location_user_roles
        self.password_reset_tokens = password_reset_tokens
        self.rls_context = rls_context
        self.emails = EmailOutbox(db)

    def list(
        self,
        *,
        location_id: UUID,
    ) -> list[StaffAccountResponse]:
        return [
            StaffAccountResponse.model_validate(row, from_attributes=True)
            for row in self.staff_accounts.list(location_id=location_id)
        ]

    @transactional
    def add(
        self,
        *,
        location_id: UUID,
        body: AddStaffRequest,
        can_make_admins: bool,
    ) -> AddStaffResponse:
        if body.role == "admin" and not can_make_admins:
            raise PermissionNotFoundError()

        # RLS shows another user only by their login email (as at login).
        self.rls_context.set_login_email(email=body.email)
        user = self.users.get_by_email(email=body.email)

        if user:
            here = self.location_user_roles.list_roles_by_user_and_location(user_id=user.id, location_id=location_id)
            existing = {role.code for role in self.roles.list_by_ids(role_ids=[r.role_id for r in here])} if here else set()

            if "customer" in existing:
                raise StaffIsFamilyHereError()

            if existing:
                raise StaffAlreadyHereError()
        else:
            user = self.users.create(
                id=uuid.uuid4(),
                email=body.email,
                # Unusable until they set their own through the invite.
                password_hash=hash_password(password=token_urlsafe(32)),
                first_name=body.first_name,
                last_name=body.last_name,
                terms_accepted_at=datetime.now(timezone.utc),
                terms_version="staff",
                is_active=True,
            )

        self.location_user_roles.create(
            user_id=user.id,
            location_id=location_id,
            role_id=self.roles.get_by_code(code=body.role).id,
        )

        invited = user.last_login is None
        if invited:
            self._invite(location_id=location_id, user=user)

        self._log("staff_added", f"user_id={user.id}; role={body.role}; invited={invited}")

        return AddStaffResponse(staff=self._one(location_id=location_id, user_id=user.id), invited=invited)

    @transactional
    def resend_invite(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> StaffAccountResponse:
        staff = self._one(location_id=location_id, user_id=user_id)
        self._managed(location_id=location_id, user_id=user_id)

        if staff.last_login is not None:
            raise StaffAlreadyActiveError()

        self.rls_context.set_login_email(email=staff.email)
        self._invite(location_id=location_id, user=self.users.get_by_email(email=staff.email))
        self._log("staff_invite_resent", f"user_id={user_id}")

        return staff

    @transactional
    def rename(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        body: RenameStaffRequest,
    ) -> StaffAccountResponse:
        self.staff_accounts.set_name(
            location_id=location_id,
            user_id=user_id,
            first_name=body.first_name,
            last_name=body.last_name,
        )
        self._log("staff_renamed", f"user_id={user_id}")

        return self._one(location_id=location_id, user_id=user_id)

    @transactional
    def change_role(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        body: ChangeStaffRoleRequest,
    ) -> StaffAccountResponse:
        self._managed(location_id=location_id, user_id=user_id)
        role_row = self.staff_accounts.staff_role(location_id=location_id, user_id=user_id)

        if not role_row:
            raise StaffNotFoundError()

        self.staff_accounts.set_role(role_row=role_row, role_id=self.roles.get_by_code(code=body.role).id)
        self._log("staff_role_changed", f"user_id={user_id}; role={body.role}")

        return self._one(location_id=location_id, user_id=user_id)

    @transactional
    def reset_pin(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> StaffAccountResponse:
        self.staff_accounts.reset_pin(location_id=location_id, user_id=user_id)
        self._log("staff_pin_reset", f"user_id={user_id}")

        return self._one(location_id=location_id, user_id=user_id)

    @transactional
    def remove(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> None:
        self.staff_accounts.remove(location_id=location_id, user_id=user_id)
        self._log("staff_removed", f"user_id={user_id}")

    def _invite(self, *, location_id: UUID, user) -> None:
        raw_token = token_urlsafe(32)

        self.password_reset_tokens.revoke_unused(user_id=user.id, location_id=location_id)
        self.password_reset_tokens.create(
            user_id=user.id,
            location_id=location_id,
            token_hash=hash_token(token=raw_token),
            expires_at=datetime.now(timezone.utc) + INVITE_LIFETIME,
        )
        self.emails.queue(StaffInviteEmail(
            location_id=location_id,
            user_id=user.id,
            to_email=user.email,
            first_name=user.first_name,
            token=raw_token,
        ))

    def _managed(self, *, location_id: UUID, user_id: UUID) -> None:
        if not self.staff_accounts.can_manage(location_id=location_id, user_id=user_id):
            raise StaffNotFoundError()

    def _one(self, *, location_id: UUID, user_id: UUID) -> StaffAccountResponse:
        for staff in self.list(location_id=location_id):
            if staff.user_id == user_id:
                return staff

        raise StaffNotFoundError()

    def _log(self, event: str, reason: str) -> None:
        logger.info("Staff account changed", extra={"event": event, "result": "success", "reason": reason})
