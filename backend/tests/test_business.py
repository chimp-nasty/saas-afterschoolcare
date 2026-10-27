"""
Business settings (/business, docs/tenant-administration.md stage 3): the
tenant's owner logs in with no location, runs the business's details and
locations, manages Stripe, and switches into a location to manage it.
"""

import uuid
from contextlib import contextmanager

import pytest

from app.auth.jwt.tokens import TokenService
from tests.factories import Api


VALID_ABN = "51824753556"

NEW_LOCATION = {
    "name": "Test Centre",
    "address_line_1": "1 Test Street",
    "suburb": "Brisbane City",
    "state": "QLD",
    "postcode": "4000",
    "timezone": "Australia/Brisbane",
}


def _business_login(api: Api, email: str = "sa1user@test.com", password: str = "123", tenant: str = "tenant1"):
    client = api.client(tenant=tenant)
    response = client.post("/auth/v1/business/login", json={"email": email, "password": password})

    return client, response


@pytest.fixture
def business(api: Api):
    """Tenant1's owner, logged in to Business settings (no location)."""
    client, response = _business_login(api)
    assert response.status_code == 200, response.text

    return client


@pytest.fixture
def tenant2_business(api: Api):
    client, response = _business_login(api, email="sa2user@test.com", tenant="tenant2")
    assert response.status_code == 200, response.text

    return client


@contextmanager
def _settings_restored(api: Api, tenant: str):
    """Business details are a shared row: put them back afterwards."""
    [before] = api.sql(
        "SELECT name, legal_name, abn, email, phone, about FROM tenancy.tenants WHERE code = :t", t=tenant
    )
    try:
        yield
    finally:
        api.sql(
            "UPDATE tenancy.tenants SET name = :name, legal_name = :legal_name, abn = :abn, "
            "email = :email, phone = :phone, about = :about WHERE code = :t",
            t=tenant,
            **before._asdict(),
        )


def _new_location(client, **changes) -> dict:
    """
    A location added through the API. Left in place afterwards, like other
    tests' new locations: a location can't be deleted once it has services
    (fk_location_services_location), and its code is unique.
    """
    code = f"new-{uuid.uuid4().hex[:8]}"
    response = client.post("/business/v1/locations", json={**NEW_LOCATION, "code": code, **changes})
    assert response.status_code == 201, response.text

    return response.json()["data"]


# ---------------------------------------------------------------------------
# Logging in
# ---------------------------------------------------------------------------


# The owner logs in to Business settings: the session has no location, but
# carries their tenant permissions.
def test_owner_logs_in_without_a_location(business):
    session = business.get("/auth/v1/session").json()["data"]

    assert session["location_code"] is None
    assert session["roles"] == []
    assert set(session["tenant_permissions"]) == {
        "tenant_settings", "tenant_locations", "tenant_stripe_account", "tenant_domains",
    }


# Anyone but the owner is refused as if the password were wrong, so the page
# doesn't say who owns the business.
def test_only_the_owner_logs_in_to_business_settings(api: Api, customer):
    _, admin = _business_login(api, email="t1user@test.com")
    _, family = _business_login(api, email=customer.email, password="Password123")
    _, wrong = _business_login(api, password="not-it")
    _, other_tenant = _business_login(api, email="sa2user@test.com")

    for response in (admin, family, wrong, other_tenant):
        assert response.status_code == 401
        assert response.json()["msg"] == wrong.json()["msg"]


# Without a location, a location's endpoints refuse the owner (no location
# permissions), even ones their superadmin role would allow there.
def test_no_location_means_no_location_permissions(business):
    assert business.get("/stripe-account/v1/").status_code == 403
    assert business.get("/staff-accounts/v1/").status_code == 403
    assert business.get("/stripe-account/v1/tenant").status_code == 200


# ---------------------------------------------------------------------------
# Switching location
# ---------------------------------------------------------------------------


# "Manage centre": the owner switches into a location and gets its roles,
# keeping their tenant permissions; no new login.
def test_owner_switches_into_a_location(business):
    response = business.post("/auth/v1/switch-location/location2")
    assert response.status_code == 200, response.text

    claims = TokenService.decode_access_token(business.cookies.get("access_token"))
    session = business.get("/auth/v1/session").json()["data"]

    assert session["location_code"] == "location2"
    assert "superadmin" in session["roles"]
    assert "tenant_settings" in claims["tenant_permissions"]
    assert business.get("/stripe-account/v1/").status_code == 200


# Switching needs a role at the destination: a staff member of location1
# can't switch into location2, and an unknown code is not found.
def test_switching_needs_a_role_there(api: Api):
    staff = api.new_staff(pin=None)

    assert staff.client.post("/auth/v1/switch-location/location2").status_code == 403
    assert staff.client.post("/auth/v1/switch-location/nowhere").status_code == 404
    assert staff.client.get("/auth/v1/session").json()["data"]["location_code"] == "location1"


# Switching needs a login.
def test_switching_needs_a_login(api: Api):
    assert api.client().post("/auth/v1/switch-location/location1").status_code == 401


# ---------------------------------------------------------------------------
# The business's details
# ---------------------------------------------------------------------------


# Every Business settings endpoint is the owner's: an admin and a
# superadmin at a location get 403.
def test_business_endpoints_are_the_owners(api: Api, admin, superadmin):
    for client in (admin, superadmin):
        assert client.get("/business/v1/overview").status_code == 403
        assert client.get("/business/v1/settings").status_code == 403
        assert client.put("/business/v1/settings", json={"name": "Taken over"}).status_code == 403
        assert client.get("/business/v1/locations").status_code == 403
        assert client.post("/business/v1/locations", json={**NEW_LOCATION, "code": "takeover"}).status_code == 403


# The overview lists the business's locations with how many services each
# offers, and whether payments are set up.
def test_overview(business):
    data = business.get("/business/v1/overview").json()["data"]

    assert {location["code"] for location in data["locations"]} >= {"location1", "location2"}
    assert data["payments_connected"] is True
    assert data["takes_payments"] is True


# The owner saves the business's details; the ABN is stored as its 11
# digits and must pass the ABN check.
def test_business_details(api: Api, business):
    body = {
        "name": "Tenant One OSHC",
        "legal_name": "Tenant One Pty Ltd",
        "abn": "51 824 753 556",
        "email": "hello@tenant1.example.com",
        "phone": "07 3000 0000",
    }

    with _settings_restored(api, "tenant1"):
        response = business.put("/business/v1/settings", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["data"]["abn"] == VALID_ABN
        assert response.json()["data"]["phone"] == "0730000000"

        assert business.get("/business/v1/overview").json()["data"]["details_complete"] is True

        bad = business.put("/business/v1/settings", json={**body, "abn": "12345678901"})
        assert bad.status_code == 400
        assert bad.json()["msg"] == "That ABN isn't valid. Check the 11 digits"


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


# A new location gets every service, none offered yet, and the owner is its
# superadmin straight away; families see it on the landing page.
def test_add_a_location(api: Api, tenant2_business):
    location = _new_location(tenant2_business)
    assert location["services_offered"] == 0

    [(services,)] = api.sql(
        "SELECT count(*) FROM public.location_services WHERE location_id = CAST(:l AS uuid)", l=location["id"]
    )
    assert services > 0

    assert tenant2_business.post(f"/auth/v1/switch-location/{location['code']}").status_code == 200
    assert "superadmin" in tenant2_business.get("/auth/v1/session").json()["data"]["roles"]

    public = api.client(tenant="tenant2").get("/location-branding/v1/public").json()["data"]
    assert location["code"] in {loc["location_code"] for loc in public}


# A code another of the business's locations uses, or one the site uses
# itself, is refused.
def test_location_codes_are_checked(tenant2_business):
    taken = tenant2_business.post("/business/v1/locations", json={**NEW_LOCATION, "code": "location2"})
    reserved = tenant2_business.post("/business/v1/locations", json={**NEW_LOCATION, "code": "business"})

    assert taken.status_code == 409
    assert reserved.status_code == 400


# Changing a location's code moves it: the old address is gone, the new
# one works.
def test_change_a_locations_code(api: Api, tenant2_business):
    location = _new_location(tenant2_business)
    new_code = f"moved-{uuid.uuid4().hex[:8]}"
    response = tenant2_business.put(
        f"/business/v1/locations/{location['id']}",
        json={**NEW_LOCATION, "code": new_code, "name": "Moved Centre"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["name"] == "Moved Centre"

    public = api.client(tenant="tenant2")
    assert public.get(f"/location-branding/v1/public/{location['code']}").status_code == 404
    assert public.get(f"/location-branding/v1/public/{new_code}").json()["data"]["location_name"] == "Moved Centre"


# One business can't edit another's location.
def test_cannot_edit_another_businesss_location(api: Api, business, tenant2_business):
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )

    response = tenant2_business.put(f"/business/v1/locations/{location_id}", json={**NEW_LOCATION, "code": "stolen"})

    assert response.status_code == 404
