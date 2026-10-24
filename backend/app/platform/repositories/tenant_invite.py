from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.db.repository import Repository
from app.db.models import TenantInvite


class TenantInviteRepository(Repository):
    """Invites (platform admins only, RLS) and registering with one."""

    def create(
        self,
        *,
        email: str,
        token_hash: str,
        created_by: UUID,
    ) -> TenantInvite:
        record = TenantInvite(
            email=email,
            token_hash=token_hash,
            created_by=created_by,
        )

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> TenantInvite | None:
        return (
            self.db.query(TenantInvite)
            .filter(TenantInvite.id == id)
            .first()
        )

    def list_pending(self) -> list[TenantInvite]:
        """Not used, revoked or expired yet; newest first."""
        return (
            self.db.query(TenantInvite)
            .filter(
                TenantInvite.used_at.is_(None),
                TenantInvite.revoked_at.is_(None),
                TenantInvite.expires_at > func.now(),
            )
            .order_by(TenantInvite.created_at.desc())
            .all()
        )

    def revoke(
        self,
        *,
        invite: TenantInvite,
    ) -> None:
        invite.revoked_at = datetime.now(timezone.utc)
        self.db.flush()

    def usable_email(
        self,
        *,
        token_hash: str,
    ) -> str | None:
        """auth.usable_invite_email: before anyone has a session."""
        return self.db.execute(
            select(func.auth.usable_invite_email(token_hash))
        ).scalar()

    def register_tenant(
        self,
        *,
        token_hash: str,
        tenant_name: str,
        tenant_code: str,
        first_name: str,
        last_name: str,
        password_hash: str,
    ) -> UUID:
        """auth.register_tenant: the tenant, its owner and the invite used, at once."""
        return self.db.execute(
            select(
                func.auth.register_tenant(
                    token_hash,
                    tenant_name,
                    tenant_code,
                    first_name,
                    last_name,
                    password_hash,
                )
            )
        ).scalar_one()
