import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token
from app.db.transaction import transactional
from app.errors.platform import InviteNotUsableError
from app.integrations.email.links import tenant_site
from app.platform.repositories.tenant_invite import TenantInviteRepository
from app.platform.schemas.platform import (
    InviteDetailsResponse,
    RegisterTenantRequest,
    RegisteredTenantResponse,
)


logger = logging.getLogger("app.platform")


class RegistrationService:
    """
    A business registering with its invite (docs/tenant-administration.md,
    stage 4). No session: the invite is the permission, and the database
    does the rest at once (auth.register_tenant).
    """

    def __init__(
        self,
        *,
        db: Session,
        tenant_invite_repository: TenantInviteRepository,
    ):
        self.db = db
        self.tenant_invite_repository = tenant_invite_repository

    def invite_details(
        self,
        *,
        token: str,
    ) -> InviteDetailsResponse:
        email = self.tenant_invite_repository.usable_email(token_hash=hash_token(token=token))

        if not email:
            raise InviteNotUsableError()

        return InviteDetailsResponse(email=email)

    @transactional
    def register(
        self,
        *,
        body: RegisterTenantRequest,
    ) -> RegisteredTenantResponse:
        """
        The tenant, its owner (the invite's email, every tenant permission)
        and the invite used up. The owner then logs in on their own site;
        the login cookie can't move there from the platform's.
        """
        tenant_id = self.tenant_invite_repository.register_tenant(
            token_hash=hash_token(token=body.invite),
            tenant_name=body.business_name,
            tenant_code=body.code,
            first_name=body.first_name,
            last_name=body.last_name,
            password_hash=hash_password(password=body.password),
        )

        logger.info(
            "Business registered",
            extra={"event": "tenant_registered", "result": "success", "reason": f"tenant_id={tenant_id}"},
        )

        return RegisteredTenantResponse(
            business_login_url=f"{tenant_site(tenant_code=body.code, custom_domain=None)}/business/login",
        )
