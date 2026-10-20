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


from tests.factories import (  # noqa: E402  (needs the env above)
    Api,
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
    ):
        monkeypatch.setattr(f"{module}.StorageClient", FakeStorage)

    return FakeStorage


@pytest.fixture(scope="session")
def api(database) -> Api:
    return Api()


# Seeded by migrations/dev_seed/0001_dev_accounts.py: admin at tenant1's
# location1, and admin at tenant2's location2.

@pytest.fixture
def admin(api: Api):
    return api.login("t1user@test.com", "123", tenant="tenant1", location="location1")


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
