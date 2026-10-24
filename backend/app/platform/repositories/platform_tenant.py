from uuid import UUID

from sqlalchemy import func, select

from app.db.repository import Repository
from app.db.models import Location, Tenant, TenantInvite, TenantStripeAccount


class PlatformTenantRepository(Repository):
    """Tenants as the platform sees them (RLS: no tenant data beyond this)."""

    def list_with_summary(self) -> list:
        """Every tenant, newest first, with its invite email, location count and Stripe state."""
        location_count = (
            select(func.count(Location.id))
            .where(Location.tenant_id == Tenant.id)
            .scalar_subquery()
        )
        invited_email = (
            select(TenantInvite.email)
            .where(TenantInvite.tenant_id == Tenant.id)
            .limit(1)
            .scalar_subquery()
        )
        payments_connected = (
            select(func.count(TenantStripeAccount.tenant_id))
            .where(TenantStripeAccount.tenant_id == Tenant.id)
            .scalar_subquery()
        )

        return self.db.execute(
            select(
                Tenant.id,
                Tenant.name,
                Tenant.code,
                Tenant.created_at,
                Tenant.is_active,
                invited_email.label("invited_email"),
                location_count.label("location_count"),
                (payments_connected > 0).label("payments_connected"),
                func.tenancy.tenant_payments_account(Tenant.id).isnot(None).label("takes_payments"),
            ).order_by(Tenant.created_at.desc())
        ).all()

    def exists(
        self,
        *,
        tenant_id: UUID,
    ) -> bool:
        return self.db.query(Tenant.id).filter(Tenant.id == tenant_id).first() is not None

    def set_active(
        self,
        *,
        tenant_id: UUID,
        is_active: bool,
    ) -> None:
        """auth.set_tenant_active: platform admins only, and only that column."""
        self.db.execute(select(func.auth.set_tenant_active(tenant_id, is_active)))
