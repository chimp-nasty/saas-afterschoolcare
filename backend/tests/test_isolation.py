"""
Row level security and permissions: users only reach their own data, and
tenants never see each other.
"""

import pytest

from app.db.session import assert_rls_enforced
from tests.factories import Api


# The database login the API uses is subject to row level security (the same
# check the app runs at startup).
def test_api_database_role_enforces_rls():
    # Same check the app runs at startup. Fails if DATABASE_URL uses a role
    # with BYPASSRLS, e.g. one created in the Neon console.
    assert_rls_enforced()


# The startup check refuses a database login that bypasses row level
# security, such as the owner role.
def test_startup_check_rejects_a_bypassing_role(api: Api, monkeypatch):
    # The owner role bypasses RLS, so the check must refuse it.
    monkeypatch.setattr("app.db.session.engine", api.admin_db)

    with pytest.raises(RuntimeError, match="bypasses row level security"):
        assert_rls_enforced()


# A customer can't fetch or list another customer's child.
def test_customer_cannot_see_another_customers_child(api: Api, customer, other_customer):
    child = api.new_child(customer)

    response = other_customer.client.get(f"/children/v1/{child['id']}")
    listed = other_customer.client.get("/children/v1/").json()["data"]

    assert response.status_code == 404
    assert child["id"] not in [c["id"] for c in listed]


# A customer can't fetch or list another customer's booking.
def test_customer_cannot_see_another_customers_booking(api: Api, customer, other_customer):
    child = api.new_child(customer)
    api.book(customer, {child["id"]: [api.service_day()]})
    [booking] = customer.client.get("/booking/v1/").json()["data"]

    response = other_customer.client.get(f"/booking/v1/{booking['id']}")
    listed = other_customer.client.get("/booking/v1/").json()["data"]

    assert response.status_code == 404
    assert listed == []


# An admin can see a customer's child at the location they're logged into.
def test_admin_sees_customers_child_at_their_location(api: Api, admin, customer):
    child = api.new_child(customer)

    response = admin.get(f"/children/v1/{child['id']}")

    assert response.status_code == 200


# An admin with roles at two locations only sees the data of the location
# they're logged into: from location2, a location1 child is hidden and the
# services are location2's own.
def test_admin_sees_only_the_session_locations_data(api: Api, admin, customer):
    # t1user is admin at both tenant1 locations. Logged into location2, a
    # location1 child and location1's services are out of scope.
    child = api.new_child(customer)
    at_location2 = api.login("t1user@test.com", "123", location="location2")

    location1_services = {s["id"] for s in admin.get("/location-services/v1/").json()["data"]}
    location2_services = {s["id"] for s in at_location2.get("/location-services/v1/").json()["data"]}

    assert at_location2.get(f"/children/v1/{child['id']}").status_code == 404
    assert len(location2_services) == 4
    assert location1_services.isdisjoint(location2_services)


# An admin logged into location2 doesn't get location1's children in the
# children list.
def test_admin_list_excludes_other_locations_children(api: Api, customer):
    # The customer belongs to location1; an admin logged into location2
    # doesn't get their children in the list.
    at_location2 = api.login("t1user@test.com", "123", location="location2")
    child = api.new_child(customer)

    listed = at_location2.get("/children/v1/").json()["data"]

    assert child["id"] not in [c["id"] for c in listed]


# An admin from another tenant (business) can't see this tenant's children.
def test_other_tenant_cannot_see_child(api: Api, tenant2_admin, customer):
    child = api.new_child(customer)

    response = tenant2_admin.get(f"/children/v1/{child['id']}")

    assert response.status_code == 404


# Each tenant only sees its own services; the two tenants' service lists
# share nothing.
def test_tenants_see_only_their_own_services(admin, tenant2_admin):
    tenant1 = {s["id"] for s in admin.get("/location-services/v1/").json()["data"]}
    tenant2 = {s["id"] for s in tenant2_admin.get("/location-services/v1/").json()["data"]}

    assert tenant1
    assert tenant2
    assert tenant1.isdisjoint(tenant2)


# A customer isn't allowed to change a service's config, such as its price
# (403 forbidden).
def test_customer_cannot_update_service_config(admin, customer):
    service_id = admin.get("/location-services/v1/").json()["data"][0]["id"]

    response = customer.client.patch(
        f"/location-services/v1/{service_id}/config",
        json={"current_price_cents": 1},
    )

    assert response.status_code == 403


# Children, bookings and actions all require logging in (401 without a
# session).
def test_routes_require_login(api: Api):
    client = api.client()

    assert client.get("/children/v1/").status_code == 401
    assert client.get("/booking/v1/").status_code == 401
    assert client.get("/action/v1/").status_code == 401
