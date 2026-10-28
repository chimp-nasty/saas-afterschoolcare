"""
Prints the Stripe connected account tenant 1 uses in the database at
DATABASE_ADMIN_URL (acct_...), or nothing if it has none. release.ps1 runs
it before rebuilding deployed dev, then hands the account to the dev seed
(STRIPE_DEV_ACCOUNT_ID) so tenant 1 stays connected without reattaching.

Run with the backend's Python (it needs SQLAlchemy and the Postgres
driver); reads only, as the database owner.
"""

import os
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    engine = create_engine(os.environ["DATABASE_ADMIN_URL"])

    try:
        with engine.connect() as conn:
            account = conn.execute(
                text(
                    """
                    SELECT a.stripe_account_id
                    FROM tenancy.tenant_stripe_accounts a
                    JOIN tenancy.tenants t
                        ON t.id = a.tenant_id
                    WHERE t.code = 'tenant1'
                      AND a.revoked_at IS NULL
                      AND a.disconnected_at IS NULL
                    """
                )
            ).scalar()
    except Exception as exc:
        # A fresh database (no tables yet): nothing to keep.
        print(f"Couldn't read tenant 1's Stripe account: {type(exc).__name__}", file=sys.stderr)
        return 0
    finally:
        engine.dispose()

    if account:
        print(account)

    return 0


if __name__ == "__main__":
    sys.exit(main())
