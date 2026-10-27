"""
Integration tests run the real app against a real (disposable) Postgres
database: a Neon branch configured in backend/.env.test.

The database is rebuilt once per session with the migrator, so tests see
the real schema, RLS policies and seed data. Each test makes its own users
through the API (unique emails), so tests don't depend on each other and
need no cleanup.
"""

import os
from pathlib import Path

import pytest
from dotenv import dotenv_values


# -------------------------------------------------------------------------
# Environment: must be set before anything imports app.core.config.
# -------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]

_test_env = dotenv_values(BACKEND_DIR / ".env.test")
_dev_env = dotenv_values(BACKEND_DIR / ".env")

_unfilled = [
    key
    for key in ("DATABASE_URL", "DATABASE_ADMIN_URL", "APP_DB_PASSWORD")
    if not _test_env.get(key) or _test_env[key].startswith("FILL_ME")
]

if _unfilled:
    pytest.exit(
        f"Fill in backend/.env.test before running tests: {', '.join(_unfilled)}",
        returncode=2,
    )

for _key in ("DATABASE_URL", "DATABASE_ADMIN_URL"):
    if _test_env[_key] == _dev_env.get(_key):
        pytest.exit(
            f"{_key} in .env.test is the same as in .env. Tests rebuild "
            "their database; point .env.test at a separate Neon branch.",
            returncode=2,
        )

os.environ.update(
    {key: value for key, value in _test_env.items() if value is not None}
)
os.environ["APP_ENV"] = "test"


from sqlalchemy import create_engine, text  # noqa: E402

from tests.factories import (  # noqa: E402  (needs the env above)
    Api,
    FakeDomains,
    FakeDomainsState,
    FakeEmail,
    FakeEmailState,
    FakeStorage,
    FakeStorageState,
    FakeStripe,
    FakeStripeState,
)


@pytest.fixture(scope="session", autouse=True)
def database():
    from migrations import migrator

    migrator.rebuild()

    # Every tenant takes payments through its own connected account, as a
    # live tenant does (tests of the other states change it and put it back).
    with create_engine(os.environ["DATABASE_ADMIN_URL"]).begin() as conn:
        conn.execute(text("""
            INSERT INTO tenancy.tenant_stripe_accounts (
                tenant_id, stripe_account_id, charges_enabled, payouts_enabled, details_submitted
            )
            SELECT t.id, 'acct_test_' || t.code, TRUE, TRUE, TRUE
            FROM tenancy.tenants t
            ON CONFLICT (tenant_id) DO UPDATE
            SET stripe_account_id = EXCLUDED.stripe_account_id,
                charges_enabled = TRUE,
                payouts_enabled = TRUE,
                details_submitted = TRUE,
                disconnected_at = NULL,
                revoked_at = NULL,
                is_linked = FALSE
        """))


@pytest.fixture(autouse=True)
def fake_stripe(monkeypatch) -> type[FakeStripe]:
    """
    Every service that talks to Stripe gets the fake instead, with fresh
    state so no test sees another test's sessions.
    """
    monkeypatch.setattr(FakeStripe, "state", FakeStripeState())

    for module in (
        "app.public.services.bookings_create",
        "app.public.services.bookings_update",
        "app.public.services.refunds_create",
        "app.integrations.payments.stripe.webhook",
        "app.integrations.payments.stripe.settlement",
        "app.tenancy.services.stripe_connect",
    ):
        monkeypatch.setattr(f"{module}.StripeClient", FakeStripe)

    return FakeStripe


@pytest.fixture(autouse=True)
def fake_email(monkeypatch) -> type[FakeEmail]:
    """
    Every email is recorded on the fake instead of sent, with fresh state
    per test. Queued emails are all sent through the outbox, so that's the
    one place to patch.
    """
    monkeypatch.setattr(FakeEmail, "state", FakeEmailState())
    monkeypatch.setattr("app.integrations.email.outbox.EmailClient", FakeEmail)

    return FakeEmail


@pytest.fixture
def sent_emails(fake_email):
    """
    The emails sent so far in this test (messages, oldest first), or only
    those of the given message types: sent_emails(ChildApprovedEmail). A
    customer fixture has already been sent a welcome email.
    """
    def sent(*types):
        return [
            message
            for message in fake_email.state.messages
            if not types or isinstance(message, types)
        ]

    return sent


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch) -> type[FakeStorage]:
    """
    Every service that stores files uses the fake bucket instead, empty for
    each test.
    """
    monkeypatch.setattr(FakeStorage, "state", FakeStorageState())

    for module in (
        "app.public.services.child_documents_create",
        "app.public.services.child_documents_read",
        "app.tenancy.services.site",
        "app.tenancy.services.centre_photo",
        "app.public.services.location_service",
    ):
        monkeypatch.setattr(f"{module}.StorageClient", FakeStorage)

    return FakeStorage


@pytest.fixture(autouse=True)
def fake_domains(monkeypatch) -> type[FakeDomains]:
    """
    The domain services use the fake cloud and DNS instead, empty for each
    test, with custom domains set up (the load balancer's address and the
    scheduler's secret).
    """
    monkeypatch.setattr(FakeDomains, "state", FakeDomainsState())

    for module in (
        "app.tenancy.services.domains",
        "app.tenancy.services.domain_check",
    ):
        monkeypatch.setattr(f"{module}.DomainsClient", FakeDomains)

    from app.core.config import settings

    monkeypatch.setattr(settings, "DOMAINS_TARGET_IP", "203.0.113.10")
    monkeypatch.setattr(settings, "DOMAINS_CHECK_SECRET", "test-domain-check-secret")

    return FakeDomains


@pytest.fixture(scope="session")
def api(database) -> Api:
    return Api()


# Seeded by migrations/dev_seed/0001_dev_accounts.py: admin at tenant1's
# location1, and admin at tenant2's location2.

@pytest.fixture
def admin(api: Api):
    return api.login("t1user@test.com", "123", tenant="tenant1", location="location1")


@pytest.fixture
def superadmin(api: Api):
    """A superadmin at tenant1/location1 (business settings), logged in on the website."""
    return api.new_staff(role="superadmin", pin=None).client


@pytest.fixture
def owner(api: Api):
    """
    Tenant1's owner (seeded: one per tenant), logged in at location1: its
    superadmin, holding every tenant permission.
    """
    return api.login("sa1user@test.com", "123", tenant="tenant1", location="location1")


@pytest.fixture
def tenant2_owner(api: Api):
    return api.login("sa2user@test.com", "123", tenant="tenant2", location="location2")


@pytest.fixture
def tenant2_admin(api: Api):
    return api.login("t2user@test.com", "123", tenant="tenant2", location="location2")


@pytest.fixture
def customer(api: Api):
    """A fresh customer at tenant1/location1 with a complete profile."""
    return api.new_customer()


@pytest.fixture
def other_customer(api: Api):
    """A second, unrelated customer at the same location."""
    return api.new_customer()


# ---------------------------------------------------------------------------
# Kiosk service times (tenancy.locations.kiosk_enforce_service_times)
# ---------------------------------------------------------------------------

LOCATION1 = (
    "FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
    "WHERE t.code = 'tenant1' AND l.code = 'location1'"
)

AFTER_SCHOOL_LOCATION1 = """
    FROM public.location_services ls
    JOIN public.service_types st ON st.id = ls.service_type_id
    JOIN tenancy.locations l ON l.id = ls.location_id
    JOIN tenancy.tenants t ON t.id = l.tenant_id
    WHERE t.code = 'tenant1' AND l.code = 'location1' AND st.code = 'after_school_care'
"""


@pytest.fixture
def service_times(api: Api):
    """
    Switches location1's kiosk service times on, and returns a way to
    move after school care's session to start some hours from now (an hour
    long). Both are put back afterwards. Skipped late at night, when moving
    the session by up to 4 hours would cross midnight.
    """
    [(hour,)] = api.sql(f"SELECT extract(hour FROM now() AT TIME ZONE l.timezone)::int {LOCATION1}")
    if not 4 <= hour < 20:
        pytest.skip("moving the session up to 4 hours from now would cross midnight")

    [(service_id, start, end)] = api.sql(
        "SELECT lsc.location_service_id::text, lsc.start_time, lsc.end_time "
        "FROM public.location_service_config lsc "
        f"WHERE lsc.location_service_id = (SELECT ls.id {AFTER_SCHOOL_LOCATION1})"
    )
    api.sql(f"UPDATE tenancy.locations SET kiosk_enforce_service_times = TRUE WHERE id = (SELECT l.id {LOCATION1})")

    def move(start_hours_from_now: int):
        api.sql(
            "UPDATE public.location_service_config lsc "
            "SET start_time = ((now() AT TIME ZONE l.timezone) + make_interval(hours => :h))::time, "
            "    end_time = ((now() AT TIME ZONE l.timezone) + make_interval(hours => :h + 1))::time "
            "FROM tenancy.locations l WHERE l.id = lsc.location_id AND lsc.location_service_id = CAST(:id AS uuid)",
            h=start_hours_from_now,
            id=service_id,
        )

    try:
        yield move
    finally:
        api.sql(
            "UPDATE public.location_service_config SET start_time = :s, end_time = :e "
            "WHERE location_service_id = CAST(:id AS uuid)",
            s=start,
            e=end,
            id=service_id,
        )
        api.sql(f"UPDATE tenancy.locations SET kiosk_enforce_service_times = FALSE WHERE id = (SELECT l.id {LOCATION1})")
