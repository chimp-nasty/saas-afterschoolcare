import logging
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.jwt.tokens import TokenService
from app.auth.repositories.rls_context import RlsContextRepository
from app.auth.schemas.auth import LoginRequest
from app.core.security import hash_token, verify_password
from app.db.transaction import transactional
from app.dependencies.platform import PlatformContext
from app.errors.auth import AuthenticationFailedError
from app.errors.platform import InviteNotFoundError, TenantNotFoundError
from app.platform.repositories.platform_admin import PlatformAdminRepository
from app.platform.repositories.platform_tenant import PlatformTenantRepository
from app.platform.repositories.tenant_invite import TenantInviteRepository
from app.platform.schemas.platform import (
    CreatedInviteResponse,
    InviteResponse,
    PlatformSessionResponse,
    PlatformTenantResponse,
)


logger = logging.getLogger("app.platform")


class PlatformService:
    """
    The platform's site (docs/tenant-administration.md, stage 4): its admins
    log in, invite businesses and switch tenants off and on. They never see
    a tenant's families, bookings or staff (RLS).
    """

    def __init__(
        self,
        *,
        db: Session,
        platform_admin_repository: PlatformAdminRepository,
        platform_tenant_repository: PlatformTenantRepository,
        tenant_invite_repository: TenantInviteRepository,
        rls_context: RlsContextRepository,
    ):
        self.db = db
        self.platform_admin_repository = platform_admin_repository
        self.platform_tenant_repository = platform_tenant_repository
        self.tenant_invite_repository = tenant_invite_repository
        self.rls_context = rls_context

    @transactional
    def login(
        self,
        *,
        body: LoginRequest,
    ) -> str:
        """A platform admin's token, or AuthenticationFailedError."""
        self.rls_context.set_login_email(email=body.email)

        admin = self.platform_admin_repository.get_by_email(email=body.email)

        if not admin or not admin.is_active:
            raise AuthenticationFailedError()

        if not verify_password(password=body.password, hashed_password=admin.password_hash):
            raise AuthenticationFailedError()

        self.rls_context.set_platform_admin_id(platform_admin_id=admin.id)
        self.platform_admin_repository.update_last_login(platform_admin=admin)

        return TokenService.create_platform_token(platform_admin_id=admin.id, email=admin.email)

    def session(
        self,
        *,
        ctx: PlatformContext,
    ) -> PlatformSessionResponse:
        return PlatformSessionResponse(platform_admin_id=ctx.platform_admin_id, email=ctx.email)

    def list_tenants(self) -> list[PlatformTenantResponse]:
        return [
            PlatformTenantResponse.model_validate(row, from_attributes=True)
            for row in self.platform_tenant_repository.list_with_summary()
        ]

    @transactional
    def set_tenant_active(
        self,
        *,
        tenant_id: UUID,
        is_active: bool,
        ctx: PlatformContext,
    ) -> None:
        """
        Switch a business off (its site and logins answer as if it didn't
        exist; data and bookings are kept; Stripe's webhooks still settle
        what's under way) or back on.
        """
        if not self.platform_tenant_repository.exists(tenant_id=tenant_id):
            raise TenantNotFoundError()

        self.platform_tenant_repository.set_active(tenant_id=tenant_id, is_active=is_active)
        self._log("tenant_activated" if is_active else "tenant_deactivated", ctx, f"tenant_id={tenant_id}")

    def list_invites(self) -> list[InviteResponse]:
        return [
            InviteResponse.model_validate(invite, from_attributes=True)
            for invite in self.tenant_invite_repository.list_pending()
        ]

    @transactional
    def create_invite(
        self,
        *,
        email: str,
        origin: str,
        ctx: PlatformContext,
    ) -> CreatedInviteResponse:
        """
        A one-time registration link for the email, to send by hand (no
        email yet). Only its hash is kept, so the link is shown once.
        """
        token = token_urlsafe(32)
        invite = self.tenant_invite_repository.create(
            email=email,
            token_hash=hash_token(token=token),
            created_by=ctx.platform_admin_id,
        )
        self._log("tenant_invite_created", ctx, f"invite_id={invite.id}")

        return CreatedInviteResponse(
            id=invite.id,
            email=invite.email,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            url=f"{origin.rstrip('/')}/register?invite={token}",
        )

    @transactional
    def revoke_invite(
        self,
        *,
        invite_id: UUID,
        ctx: PlatformContext,
    ) -> None:
        invite = self.tenant_invite_repository.get_by_id(id=invite_id)

        if not invite or invite.used_at or invite.revoked_at:
            raise InviteNotFoundError()

        self.tenant_invite_repository.revoke(invite=invite)
        self._log("tenant_invite_revoked", ctx, f"invite_id={invite_id}")

    def _log(self, event: str, ctx: PlatformContext, reason: str) -> None:
        logger.info(
            "Platform change",
            extra={"event": event, "result": "success", "reason": f"platform_admin_id={ctx.platform_admin_id}; {reason}"},
        )
