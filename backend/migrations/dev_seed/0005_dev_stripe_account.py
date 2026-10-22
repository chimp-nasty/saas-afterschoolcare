"""
Dev only: link tenant1 to a Stripe test-mode connected account, so a
rebuild doesn't need onboarding again (docs: infra/stripe/README.md).

Set STRIPE_DEV_ACCOUNT_ID in the backend's .env to the account's id
(acct_...), after connecting it once through Admin › Payments. Without it,
nothing is linked: tenant1 isn't taking bookings until a superadmin
(sa1user@test.com) connects Stripe there.

The flags are written as ready; Admin › Payments' "Refresh" (or Stripe's
account.updated webhook) corrects them from Stripe.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import settings


def up(conn: Connection) -> None:
    if not settings.STRIPE_DEV_ACCOUNT_ID:
        return

    conn.execute(
        text("""
            INSERT INTO tenancy.tenant_stripe_accounts (
                tenant_id, stripe_account_id, charges_enabled, payouts_enabled, details_submitted
            )
            SELECT t.id, :account_id, TRUE, TRUE, TRUE
            FROM tenancy.tenants t
            WHERE t.code = 'tenant1'
            ON CONFLICT (tenant_id) DO UPDATE
            SET stripe_account_id = EXCLUDED.stripe_account_id,
                charges_enabled = TRUE,
                payouts_enabled = TRUE,
                details_submitted = TRUE,
                disconnected_at = NULL,
                revoked_at = NULL;
        """),
        {"account_id": settings.STRIPE_DEV_ACCOUNT_ID},
    )
