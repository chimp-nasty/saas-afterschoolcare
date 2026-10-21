"""
Admins managing their location's kiosk tablets (/kiosk-devices/v1): at most
one active family kiosk and one staff kiosk, each paired with a one-time
setup code. Only admins of the location can add, re-pair or revoke them.
"""

import re

import pytest

from tests.factories import Api


BASE = "/kiosk/v1/location1"


@pytest.fixture(autouse=True)
def no_kiosks(api: Api):
    """Start each test with no active kiosks at location1 (shared rows)."""
    api.sql(
        "UPDATE public.location_kiosk_devices d SET is_active = FALSE "
        "FROM tenancy.locations l WHERE d.location_id = l.id AND l.code = 'location1'"
    )


def _add(admin, kind: str = "family"):
    return admin.post("/kiosk-devices/v1/", json={"kind": kind, "name": f"{kind} tablet"})


# Adding a kiosk gives a one-time setup code: 8 uppercase letters and
# digits, without lookalikes, and the kiosk waits to be paired.
def test_admin_adds_a_kiosk(admin):
    response = _add(admin)
    assert response.status_code == 201, response.text

    data = response.json()["data"]
    assert re.fullmatch(r"[A-HJ-KM-NP-Z2-9]{8}", data["setup_code"])
    assert data["device"]["paired_at"] is None
    assert data["device"]["setup_code_expires_at"] is not None


# A location has one active kiosk of each kind: a second family kiosk is
# refused, but a staff kiosk alongside it is fine.
def test_one_active_kiosk_of_each_kind(admin):
    assert _add(admin, "family").status_code == 201
    assert _add(admin, "family").status_code == 409
    assert _add(admin, "staff").status_code == 201


# Once revoked, a kiosk no longer counts, so a replacement can be added.
def test_revoked_kiosk_can_be_replaced(admin):
    device = _add(admin).json()["data"]["device"]

    assert admin.post(f"/kiosk-devices/v1/{device['id']}/revoke").status_code == 200
    assert _add(admin).status_code == 201


# A new setup code re-pairs the kiosk: the old tablet stops working, the
# one paired with the new code works.
def test_new_setup_code_repairs_the_kiosk(api: Api, admin):
    old_tablet = api.kiosk(admin, "family")
    [device] = [d for d in admin.get("/kiosk-devices/v1/").json()["data"] if d["is_active"] and d["kind"] == "family"]

    code = admin.post(f"/kiosk-devices/v1/{device['id']}/setup-code").json()["data"]["setup_code"]
    new_tablet = api.client()

    assert old_tablet.get(f"{BASE}/device").status_code == 401
    assert new_tablet.post(f"{BASE}/pair", json={"code": code}).status_code == 200
    assert new_tablet.get(f"{BASE}/device").status_code == 200


# A setup code only pairs a tablet at its own location.
def test_setup_code_only_works_at_its_location(api: Api, admin):
    code = _add(admin).json()["data"]["setup_code"]

    other_site = api.client(tenant="tenant2")
    assert other_site.post("/kiosk/v1/location2/pair", json={"code": code}).status_code == 400


# Families can't see or add kiosks.
def test_customers_cannot_manage_kiosks(customer):
    assert customer.client.get("/kiosk-devices/v1/").status_code == 403
    assert customer.client.post("/kiosk-devices/v1/", json={"kind": "family", "name": "x"}).status_code == 403


# Another tenant's admin can't see or revoke this location's kiosks.
def test_other_tenant_cannot_touch_kiosks(admin, tenant2_admin):
    device = _add(admin).json()["data"]["device"]

    ids = [d["id"] for d in tenant2_admin.get("/kiosk-devices/v1/").json()["data"]]
    assert device["id"] not in ids
    assert tenant2_admin.post(f"/kiosk-devices/v1/{device['id']}/revoke").status_code == 404
