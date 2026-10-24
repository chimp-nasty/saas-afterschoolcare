from uuid import UUID
from secrets import token_urlsafe
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, hash_token
from app.auth.jwt.tokens import TokenService
from app.auth.jwt.context import PermissionMap
from app.db.transaction import transactional
from app.integrations.email.messages import PasswordChangedEmail, PasswordResetEmail
from app.integrations.email.outbox import EmailOutbox
from app.auth.repositories.user import UserRepository
from app.auth.repositories.permission import PermissionRepository
from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.role import RoleRepository
from app.auth.repositories.password_reset_token import PasswordResetTokenRepository
from app.auth.repositories.rls_context import RlsContextRepository
from app.auth.jwt.context import TokenContext
from app.tenancy.repositories.location import LocationRepository
from app.auth.schemas.auth import (
    LoginRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    SessionResponse,
)
from app.errors.auth import (
    AuthenticationFailedError,
    PermissionNotFoundError,
    InvalidPasswordResetError,
    JwtInvalidError,
)


class AuthService:
    def __init__(
        self,
        *,
        db: Session,
        users: UserRepository,
        permissions: PermissionRepository,
        roles: RoleRepository,
        location_user_roles: LocationUserRoleRepository,
        password_reset_tokens: PasswordResetTokenRepository,
        rls_context: RlsContextRepository,
        locations: LocationRepository,
    ):
        self.db = db
        self.users = users
        self.permissions = permissions
        self.roles = roles
        self.location_user_roles = location_user_roles
        self.password_reset_tokens = password_reset_tokens
        self.rls_context = rls_context
        self.locations = locations
        self.emails = EmailOutbox(db)

    def get_session(
        self,
        *,
        ctx: TokenContext,
    ) -> SessionResponse:
        """
        Who's logged in, at which location (none in Business settings), and
        what they may do across the tenant (from their token).
        """
        location = None

        if ctx.location_id:
            location = self.locations.get_by_id(id=ctx.location_id)

            if not location:
                raise JwtInvalidError()

        return SessionResponse(
            user_id=ctx.user_id,
            email=ctx.email,
            first_name=ctx.first_name,
            roles=ctx.roles,
            location_id=location.id if location else None,
            location_code=location.code if location else None,
            location_name=location.name if location else None,
            tenant_permissions={
                resource: sorted(actions)
                for resource, actions in ctx.tenant_permissions.items()
            },
        )

    @transactional
    def login(
        self,
        *,
        body: LoginRequest,
        location_id: UUID,
    ) -> str:
        """
        Authenticate a user for a location and issue an access token.

        The token contains the user's roles and effective permissions
        for the requested location, and their permissions across its
        tenant (the owner's; empty for everyone else).
        """
        user = self._authenticate(body=body)

        if not self.location_user_roles.list_roles_by_user_and_location(
            user_id=user.id,
            location_id=location_id,
        ):
            raise AuthenticationFailedError()

        self.users.update_last_login(
            user=user,
        )

        location = self.locations.get_by_id(id=location_id)

        return self._issue_token(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            tenant_id=location.tenant_id,
            location_id=location_id,
        )

    @transactional
    def business_login(
        self,
        *,
        body: LoginRequest,
        tenant_id: UUID,
    ) -> str:
        """
        Log in to Business settings (/business): the tenant's owner only,
        with no location (docs/tenant-administration.md). Anyone else is
        refused as if the password were wrong, so the page doesn't say who
        owns the business.
        """
        user = self._authenticate(body=body)

        if not self.permissions.list_tenant_permissions(
            user_id=user.id,
            tenant_id=tenant_id,
        ):
            raise AuthenticationFailedError()

        self.users.update_last_login(
            user=user,
        )

        return self._issue_token(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            tenant_id=tenant_id,
            location_id=None,
        )

    @transactional
    def switch_location(
        self,
        *,
        ctx: TokenContext,
        location_id: UUID,
    ) -> str:
        """
        A new token for another location of the same tenant (the site's,
        resolve_location_id) where the user has a role, keeping their
        tenant permissions: "Manage centre" from Business settings. Tenant
        permissions never stand in for a role there.
        """
        self.rls_context.set_user_id(
            user_id=ctx.user_id,
        )

        if not self.location_user_roles.list_roles_by_user_and_location(
            user_id=ctx.user_id,
            location_id=location_id,
        ):
            raise PermissionNotFoundError()

        return self._issue_token(
            user_id=ctx.user_id,
            email=ctx.email,
            first_name=ctx.first_name,
            tenant_id=ctx.tenant_id,
            location_id=location_id,
        )

    def _authenticate(
        self,
        *,
        body: LoginRequest,
    ):
        """The user with this email and password (RLS set to them), or AuthenticationFailedError."""
        self.rls_context.set_login_email(
            email=body.email,
        )

        user = self.users.get_by_email(
            email=body.email,
        )

        if not user:
            raise AuthenticationFailedError()

        if not verify_password(
            password=body.password,
            hashed_password=user.password_hash,
        ):
            raise AuthenticationFailedError()

        self.rls_context.set_user_id(
            user_id=user.id,
        )

        return user

    def _issue_token(
        self,
        *,
        user_id: UUID,
        email: str | None,
        first_name: str | None,
        tenant_id: UUID,
        location_id: UUID | None,
    ) -> str:
        """
        Every access token is made here (location login, business login,
        switching location), so the claims can't drift: the roles and
        permissions at the location (none without one) and the tenant
        permissions, read now.
        """
        roles: list[str] = []
        permission_map: PermissionMap = {}

        if location_id:
            role_ids = [
                location_role.role_id
                for location_role in self.location_user_roles.list_roles_by_user_and_location(
                    user_id=user_id,
                    location_id=location_id,
                )
            ]

            roles = [
                role.code
                for role in self.roles.list_by_ids(
                    role_ids=role_ids,
                )
            ]

            permission_map = self._build_permission_map(
                permissions=self.permissions.list_by_role_ids(
                    role_ids=role_ids,
                ),
            )

        tenant_permission_map = self._build_permission_map(
            permissions=self.permissions.list_tenant_permissions(
                user_id=user_id,
                tenant_id=tenant_id,
            ),
        )

        return TokenService.create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            location_id=location_id,
            roles=roles,
            permissions=permission_map,
            tenant_permissions=tenant_permission_map,
            email=email,
            first_name=first_name,
        )

    def _build_permission_map(
        self,
        *,
        permissions,
    ) -> PermissionMap:
        permission_map: dict[str, set[str]] = {}

        for permission in permissions:
            permission_map.setdefault(
                permission.resource,
                set(),
            ).add(
                permission.action,
            )

        return {
            resource: frozenset(actions)
            for resource, actions in permission_map.items()
        }

    @transactional
    def reset_password(
        self,
        *,
        body: ResetPasswordRequest
    ) -> None:
        """
        Reset a user's password using a valid reset token.

        Validates the reset token, resolves the associated user,
        updates the password, and marks the token as used.
        """
        token_hash = hash_token(
            token=body.token
        )

        reset_token = self.password_reset_tokens.get_valid_by_token_hash(
            token_hash=token_hash,
        )

        if not reset_token:
            raise InvalidPasswordResetError()

        # RLS only shows a user their own row, so act as the token's user.
        # The token's foreign key guarantees the user exists.
        self.rls_context.set_user_id(
            user_id=reset_token.user_id,
        )

        user = self.users.get_by_id(
            id=reset_token.user_id,
        )

        password_hash = hash_password(
            password=body.password
        )

        self.users.update_password_hash(
            user=user,
            password_hash=password_hash
        )

        self.password_reset_tokens.mark_used(
            token=reset_token,
        )

        # From the centre the reset was requested at.
        self.emails.queue(PasswordChangedEmail(
            location_id=reset_token.location_id,
            user_id=user.id,
            to_email=user.email,
            first_name=user.first_name,
        ))

    @transactional
    def request_password_reset(
        self,
        *,
        body: ForgotPasswordRequest,
        location_id: UUID,
    ) -> None:
        """
        Email a reset link to a user who can log in at this location.

        Anyone else (an unknown email, or a user of another location) gets
        nothing, and the caller can't tell the difference: the route answers
        the same either way. Only the token's hash is stored; the raw token
        exists only in the email.
        """
        # RLS hides users until the lookup email is set (see login).
        self.rls_context.set_login_email(
            email=body.email,
        )

        user = self.users.get_by_email(
            email=body.email
        )

        if not user:
            return

        self.rls_context.set_user_id(
            user_id=user.id,
        )

        # Logins are per location, so a reset is too.
        if not self.location_user_roles.list_roles_by_user_and_location(
            user_id=user.id,
            location_id=location_id,
        ):
            return

        raw_token = token_urlsafe(32)

        token_hash = hash_token(
            token=raw_token,
        )

        self.password_reset_tokens.create(
            user_id=user.id,
            location_id=location_id,
            token_hash=token_hash,
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=30)
            ),
        )

        self.emails.queue(PasswordResetEmail(
            location_id=location_id,
            user_id=user.id,
            to_email=user.email,
            first_name=user.first_name,
            token=raw_token,
        ))
