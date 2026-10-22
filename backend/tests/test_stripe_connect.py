"""
Stripe Connect (Admin › Payments, slice 5): each tenant is paid into its
own Stripe account. Superadmins connect it through Stripe's onboarding and
can turn payments off and on; admins see whether it takes payments. A
centre takes bookings only while its account can take payments. Payments
and refunds happen in the tenant's account, and only events from that
account settle them. Refunds of past payments still work after payments
are turned off, but not once the business revokes our access in Stripe.

Each tenant has a connected account for tests (conftest). Tests that
change one put it back.
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.payments.stripe.client import StripeAccount
from tests.factories import Api


BASE = "/stripe-account/v1"


@contextmanager
def _account_changed(api: Api, tenant: str):
    """Restores the tenant's test account afterwards, whatever the test did to it."""
    try:
        yield
    finally:
        api.sql(
            """
            INSERT INTO tenancy.tenant_stripe_accounts (
                tenant_id, stripe_account_id, charges_enabled, payouts_enabled, details_submitted
            )
            SELECT t.id, 'acct_test_' || t.code, TRUE, TRUE, TRUE
            FROM tenancy.tenants t
            WHERE t.code = :tenant
            ON CONFLICT (tenant_id) DO UPDATE
            SET stripe_account_id = EXCLUDED.stripe_account_id,
                charges_enabled = TRUE, payouts_enabled = TRUE, details_submitted = TRUE,
                disconnected_at = NULL, revoked_at = NULL
            """,
            tenant=tenant,
        )


def _paid_booking(api: Api, customer) -> str:
    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 201, response.text
    api.webhook("checkout.session.completed", api.session_id(response.json()["data"]["checkout_url"]))

    [(booking_id,)] = api.sql(
        "SELECT id::text FROM public.bookings WHERE booking_group_id = :g",
        g=response.json()["data"]["booking_group_id"],
    )

    return booking_id


# Admins and superadmins see whether the business takes payments; staff
# on the website and families don't.
def test_who_sees_the_status(api: Api, admin, superadmin, customer):
    data = admin.get(f"{BASE}/").json()["data"]
    assert (data["connected"], data["takes_payments"]) == (True, True)

    assert superadmin.get(f"{BASE}/").status_code == 200
    assert api.new_staff(pin=None).client.get(f"{BASE}/").status_code == 403
    assert customer.client.get(f"{BASE}/").status_code == 403


# Only superadmins connect or turn payments off.
def test_admins_cannot_change_it(admin):
    assert admin.post(f"{BASE}/onboarding").status_code == 403
    assert admin.post(f"{BASE}/disconnect").status_code == 403


# A checkout is made in the tenant's own account, and only an event from
# that account (the Connect endpoint) confirms it.
def test_payments_go_to_the_tenants_account(api: Api, customer, fake_stripe):
    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]})
    data = response.json()["data"]
    session_id = api.session_id(data["checkout_url"])

    assert fake_stripe.state.created[-1]["account_id"] == "acct_test_tenant1"

    # The same event, but from the platform's own endpoint: ignored.
    fake_stripe.state.session_accounts[session_id] = None
    api.webhook("checkout.session.completed", session_id)
    [(status,)] = api.sql("SELECT booking_status::text FROM public.bookings WHERE booking_group_id = :g", g=data["booking_group_id"])
    assert status == "PENDING"

    fake_stripe.state.session_accounts[session_id] = "acct_test_tenant1"
    api.webhook("checkout.session.completed", session_id)
    [(status,)] = api.sql("SELECT booking_status::text FROM public.bookings WHERE booking_group_id = :g", g=data["booking_group_id"])
    assert status == "CONFIRMED"


# A new business connects: a Standard account is created and the
# superadmin is sent to Stripe's onboarding, returning to Admin › Payments.
# Bookings open once Stripe says the account can take payments.
def test_connecting_a_business(api: Api, fake_stripe):
    superadmin = api.new_staff(role="superadmin", pin=None, tenant="tenant2", location="location2").client
    customer = api.new_customer(tenant="tenant2", location="location2")
    child = api.new_child(customer)
    day = api.service_day(tenant="tenant2", location="location2")

    with _account_changed(api, "tenant2"):
        api.sql("DELETE FROM tenancy.tenant_stripe_accounts WHERE tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant2')")

        assert superadmin.get(f"{BASE}/").json()["data"]["connected"] is False
        refused = api.book(customer, {child["id"]: [day]})
        assert refused.status_code == 409
        assert refused.json()["msg"] == "This centre isn't taking bookings online yet"

        response = superadmin.post(f"{BASE}/onboarding")
        assert response.status_code == 200, response.text
        [account_id] = fake_stripe.state.accounts
        assert response.json()["data"]["url"].endswith(account_id)
        assert fake_stripe.state.onboarding_links[-1]["return_url"].endswith("/location2/admin/payments?stripe=return")

        status = superadmin.get(f"{BASE}/").json()["data"]
        assert (status["connected"], status["takes_payments"]) == (True, False)

        # Onboarding finished: Stripe's account.updated turns payments on.
        event = {
            "type": "account.updated",
            "data": {"object": {"id": account_id, "charges_enabled": True, "payouts_enabled": True, "details_submitted": True}},
        }
        assert api._deliver(event, account_id).status_code == 200
        assert superadmin.get(f"{BASE}/").json()["data"]["takes_payments"] is True
        assert api.book(customer, {child["id"]: [day]}).status_code == 201


# Turning payments off stops new bookings, but a past payment can still be
# refunded through the account it was made in; turning them on reopens.
def test_disconnect_keeps_refunds(api: Api, superadmin, customer, fake_stripe):
    booking_id = _paid_booking(api, customer)

    with _account_changed(api, "tenant1"):
        data = superadmin.post(f"{BASE}/disconnect").json()["data"]
        assert (data["disconnected"], data["takes_payments"]) == (True, False)

        child = api.new_child(customer)
        assert api.book(customer, {child["id"]: [api.service_day()]}).status_code == 409

        response = customer.client.post("/refunds/v1/", json={"booking_id": booking_id})
        assert response.status_code == 201, response.text
        [refund] = fake_stripe.state.refunds.values()
        assert refund["account_id"] == "acct_test_tenant1"

        assert superadmin.post(f"{BASE}/reconnect").json()["data"]["takes_payments"] is True


# Once the business revokes our access in Stripe, bookings close and a
# past payment can only be refunded in their own Stripe dashboard.
def test_revoked_access(api: Api, customer):
    booking_id = _paid_booking(api, customer)

    with _account_changed(api, "tenant1"):
        event = {"type": "account.application.deauthorized", "data": {"object": {"id": "ca_test"}}}
        assert api._deliver(event, "acct_test_tenant1").status_code == 200

        response = customer.client.post("/refunds/v1/", json={"booking_id": booking_id})
        assert response.status_code == 409
        assert "Stripe dashboard" in response.json()["msg"]

        child = api.new_child(customer)
        assert api.book(customer, {child["id"]: [api.service_day()]}).status_code == 409


# The account flags can only be changed by Stripe's webhooks (server code),
# never from a user's session.
def test_flags_only_from_stripe(api: Api):
    [(admin_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = 't1user@test.com'")

    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": admin_id})

        with pytest.raises(DBAPIError, match="Only Stripe"):
            db.execute(text("SELECT tenancy.sync_stripe_account('acct_test_tenant1', FALSE, FALSE, FALSE, FALSE)"))


# ---------------------------------------------------------------------------
# "Connect with Stripe": linking an existing account (OAuth)
# ---------------------------------------------------------------------------


@pytest.fixture
def oauth_enabled(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_CONNECT_CLIENT_ID", "ca_test")


def _start_oauth(superadmin, fake_stripe) -> str:
    """Start "Connect with Stripe"; returns the state Stripe will hand back."""
    response = superadmin.post(f"{BASE}/oauth")
    assert response.status_code == 200, response.text
    assert fake_stripe.state.oauth_links[-1]["redirect_uri"].endswith("/stripe-account/v1/oauth/callback")

    return fake_stripe.state.oauth_links[-1]["state"]


def _finish_oauth(api: Api, **params):
    return api.client().get(f"{BASE}/oauth/callback", params=params, follow_redirects=False)


# A superadmin links the business's existing Stripe account: Stripe returns
# to the API's callback (no login needed; the signed state says who and
# where), the account is linked, and they land back on Admin › Payments.
def test_link_an_existing_account(api: Api, superadmin, fake_stripe, oauth_enabled):
    fake_stripe.state.accounts["acct_existing"] = StripeAccount(
        account_id="acct_existing", charges_enabled=True, payouts_enabled=True, details_submitted=True
    )
    fake_stripe.state.oauth_codes["ac_good"] = "acct_existing"

    with _account_changed(api, "tenant1"):
        assert superadmin.get(f"{BASE}/").json()["data"]["can_link_existing"] is True
        state = _start_oauth(superadmin, fake_stripe)

        response = _finish_oauth(api, code="ac_good", state=state, scope="read_write")
        assert response.status_code == 303
        assert response.headers["location"].endswith("/location1/admin/payments?stripe=connected")

        status = superadmin.get(f"{BASE}/").json()["data"]
        assert (status["stripe_account_id"], status["takes_payments"]) == ("acct_existing", True)


# Declining at Stripe, or a code that fails, sends them back saying so;
# nothing is linked.
def test_cancelled_or_failed_link(api: Api, superadmin, fake_stripe, oauth_enabled):
    state = _start_oauth(superadmin, fake_stripe)

    cancelled = _finish_oauth(api, error="access_denied", state=state)
    assert cancelled.headers["location"].endswith("?stripe=cancelled")

    failed = _finish_oauth(api, code="ac_unknown", state=state)
    assert failed.headers["location"].endswith("?stripe=error")

    assert superadmin.get(f"{BASE}/").json()["data"]["stripe_account_id"] == "acct_test_tenant1"


# One Stripe account can't be linked to two businesses.
def test_account_already_linked_elsewhere(api: Api, superadmin, fake_stripe, oauth_enabled):
    fake_stripe.state.accounts["acct_test_tenant2"] = StripeAccount(
        account_id="acct_test_tenant2", charges_enabled=True, payouts_enabled=True, details_submitted=True
    )
    fake_stripe.state.oauth_codes["ac_taken"] = "acct_test_tenant2"

    with _account_changed(api, "tenant1"):
        response = _finish_oauth(api, code="ac_taken", state=_start_oauth(superadmin, fake_stripe))

        assert response.headers["location"].endswith("?stripe=taken")


# A callback without a valid state (forged, expired, or another app's) goes
# nowhere and links nothing.
def test_callback_needs_our_state(api: Api):
    response = _finish_oauth(api, code="ac_good", state="forged")

    assert response.status_code == 400


# Without the platform's OAuth client id, linking isn't offered.
def test_linking_needs_the_client_id(superadmin, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_CONNECT_CLIENT_ID", None)

    assert superadmin.get(f"{BASE}/").json()["data"]["can_link_existing"] is False
    assert superadmin.post(f"{BASE}/oauth").status_code == 409
