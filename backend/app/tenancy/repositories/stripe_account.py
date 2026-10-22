from uuid import UUID

from sqlalchemy import func, select

from app.db.models import TenantStripeAccount
from app.db.repository import Repository


class TenantStripeAccountRepository(Repository):
    """
    A tenant's connected Stripe account (tenancy.tenant_stripe_accounts,
    schema/0002). RLS: readable by anyone with a role at one of the
    tenant's locations; written by its superadmins. Stripe's webhooks
    update it through tenancy.sync_stripe_account (server code only).
    """

    def get_for_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> TenantStripeAccount | None:
        return (
            self.db.query(TenantStripeAccount)
            .filter(TenantStripeAccount.tenant_id == tenant_id)
            .first()
        )

    def connect(
        self,
        *,
        tenant_id: UUID,
        stripe_account_id: str,
        charges_enabled: bool,
        payouts_enabled: bool,
        details_submitted: bool,
    ) -> TenantStripeAccount:
        """A new connected account for the tenant, replacing a revoked one."""
        account = self.get_for_tenant(tenant_id=tenant_id) or TenantStripeAccount(tenant_id=tenant_id)

        account.stripe_account_id = stripe_account_id
        account.charges_enabled = charges_enabled
        account.payouts_enabled = payouts_enabled
        account.details_submitted = details_submitted
        account.connected_at = func.now()
        account.disconnected_at = None
        account.revoked_at = None

        self.db.add(account)
        self.db.flush()
        self.db.refresh(account)

        return account

    def set_flags(
        self,
        *,
        account: TenantStripeAccount,
        charges_enabled: bool,
        payouts_enabled: bool,
        details_submitted: bool,
    ) -> None:
        account.charges_enabled = charges_enabled
        account.payouts_enabled = payouts_enabled
        account.details_submitted = details_submitted

        self.db.flush()

    def set_disconnected(
        self,
        *,
        account: TenantStripeAccount,
        disconnected: bool,
    ) -> None:
        """Turn payments off in our app (or back on); the account stays linked for refunds."""
        account.disconnected_at = func.now() if disconnected else None

        self.db.flush()
        self.db.refresh(account)

    def sync(
        self,
        *,
        stripe_account_id: str,
        charges_enabled: bool = False,
        payouts_enabled: bool = False,
        details_submitted: bool = False,
        revoked: bool = False,
    ) -> bool:
        """What Stripe says about an account (webhooks only). False if it isn't one of ours."""
        return bool(
            self.db.execute(
                select(
                    func.tenancy.sync_stripe_account(
                        stripe_account_id,
                        charges_enabled,
                        payouts_enabled,
                        details_submitted,
                        revoked,
                    )
                )
            ).scalar()
        )
