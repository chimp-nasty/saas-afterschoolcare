"""
Staff accounts (Admin › Staff, slice 4-3). Admins and superadmins see the
location's staff, add staff (new accounts get an invite to set their
password), resend invites, correct names and reset staff PINs; superadmins
also make or unmake admins and remove people. The database keeps a
location safe whoever does it: no superadmins changed here, nobody changes
their own role, and there's always an admin.
"""

import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from app.integrations.email.messages import StaffInviteEmail
from tests.factories import Api


BASE = "/staff-accounts/v1"


def _email() -> str:
    return f"new-staff-{uuid.uuid4().hex[:12]}@test.com"


def _add(client, email: str, role: str = "staff"):
    return client.post(f"{BASE}/", json={"email": email, "first_name": "Robin", "last_name": "Lee", "role": role})


def _listed(client, user_id: str) -> dict | None:
    return next((s for s in client.get(f"{BASE}/").json()["data"] if s["user_id"] == user_id), None)


def _invite_token(sent_emails, email: str) -> str:
    return [m.token for m in sent_emails(StaffInviteEmail) if m.to_email == email][-1]


# An admin adds a staff member: they're listed as invited, and the invite
# link sets their password so they can log in.
def test_add_staff_and_accept_the_invite(api: Api, admin, sent_emails):
    email = _email()

    response = _add(admin, email)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["invited"] is True
    assert (data["staff"]["role_code"], data["staff"]["last_login"], data["staff"]["has_pin"]) == ("staff", None, False)

    accepted = api.client().post(
        "/auth/v1/reset-password",
        json={"token": _invite_token(sent_emails, email), "password": "Welcome123"},
    )
    assert accepted.status_code == 200, accepted.text
    assert api.login(email, "Welcome123").get("/account/v1/").status_code == 200


# Making someone an admin is a superadmin's: an admin can't add one, a
# superadmin can.
def test_only_superadmins_add_admins(admin, superadmin):
    assert _add(admin, _email(), role="admin").status_code == 403

    response = _add(superadmin, _email(), role="admin")
    assert response.status_code == 201, response.text
    assert response.json()["data"]["staff"]["role_code"] == "admin"


# Someone who already has an account (here, staff at another of the
# business's centres) is added without an invite; they log in as they do.
def test_existing_account_is_added_without_an_invite(api: Api, admin, sent_emails):
    elsewhere = api.new_staff(pin=None, location="location2")

    response = _add(admin, elsewhere.email)

    assert response.status_code == 201, response.text
    assert response.json()["data"]["invited"] is False
    assert [m for m in sent_emails(StaffInviteEmail) if m.to_email == elsewhere.email] == []


# A family's account at this centre, or someone already on its staff,
# can't be added.
def test_cannot_add_a_family_here_or_existing_staff(api: Api, admin, customer):
    assert _add(admin, customer.email).status_code == 409

    staff = api.new_staff(pin=None)
    assert _add(admin, staff.email).status_code == 409


# Resending an invite makes a new link and stops the old one; someone who's
# already logged in uses Forgot password instead.
def test_resend_invite(api: Api, admin, sent_emails):
    email = _email()
    user_id = _add(admin, email).json()["data"]["staff"]["user_id"]
    first = _invite_token(sent_emails, email)

    assert admin.post(f"{BASE}/{user_id}/invite").status_code == 200
    second = _invite_token(sent_emails, email)
    assert second != first

    assert api.client().post("/auth/v1/reset-password", json={"token": first, "password": "Welcome123"}).status_code != 200
    assert api.client().post("/auth/v1/reset-password", json={"token": second, "password": "Welcome123"}).status_code == 200

    api.login(email, "Welcome123")
    assert admin.post(f"{BASE}/{user_id}/invite").status_code == 409


# Admins correct a staff member's name.
def test_correct_a_name(api: Api, admin):
    staff = api.new_staff(pin=None)

    response = admin.patch(f"{BASE}/{staff.user_id}", json={"first_name": "Sammy"})

    assert response.status_code == 200, response.text
    assert response.json()["data"]["first_name"] == "Sammy"


# Superadmins make staff admins and back; admins can't.
def test_change_role(api: Api, admin, superadmin):
    staff = api.new_staff(pin=None)

    assert admin.put(f"{BASE}/{staff.user_id}/role", json={"role": "admin"}).status_code == 403

    response = superadmin.put(f"{BASE}/{staff.user_id}/role", json={"role": "admin"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["role_code"] == "admin"

    assert superadmin.put(f"{BASE}/{staff.user_id}/role", json={"role": "staff"}).json()["data"]["role_code"] == "staff"


# Resetting a staff PIN clears it; the staff member sets a new one on
# their account page as before.
def test_reset_staff_pin(api: Api, admin):
    staff = api.new_staff()
    assert _listed(admin, staff.user_id)["has_pin"] is True

    assert admin.post(f"{BASE}/{staff.user_id}/reset-pin").status_code == 200
    assert _listed(admin, staff.user_id)["has_pin"] is False

    assert staff.client.put("/staff-pin/v1/", json={"password": "Password123", "pin": "1470"}).status_code == 200


# A superadmin removes someone: they're off the list, their open shift is
# closed, and they can't log in here; their account stays. Admins can't.
def test_remove_staff(api: Api, admin, superadmin):
    staff = api.new_staff()
    tablet = api.kiosk(admin, "staff")
    tablet.post(
        "/staff-kiosk/v1/location1/shift",
        json={"action": "start"},
        headers={"X-Kiosk-Staff": staff.user_id, "X-Kiosk-Pin": staff.pin},
    )

    assert admin.delete(f"{BASE}/{staff.user_id}").status_code == 403

    response = superadmin.delete(f"{BASE}/{staff.user_id}")
    assert response.status_code == 200, response.text
    assert _listed(superadmin, staff.user_id) is None

    [(open_shifts,)] = api.sql(
        "SELECT count(*) FROM public.staff_shifts WHERE user_id = CAST(:id AS uuid) AND ended_at IS NULL",
        id=staff.user_id,
    )
    assert open_shifts == 0
    assert api.client().post(
        "/auth/v1/login/location1",
        json={"email": staff.email, "password": "Password123"},
    ).status_code == 401
    assert api.sql("SELECT 1 FROM auth.users WHERE id = CAST(:id AS uuid)", id=staff.user_id)


# Superadmins are listed but not managed here: not renamed, reset, changed
# or removed.
def test_superadmins_are_not_managed_here(api: Api, superadmin):
    other = api.new_staff(role="superadmin", pin=None)

    assert _listed(superadmin, other.user_id)["role_code"] == "superadmin"
    assert superadmin.patch(f"{BASE}/{other.user_id}", json={"first_name": "X"}).status_code == 404
    assert superadmin.put(f"{BASE}/{other.user_id}/role", json={"role": "staff"}).status_code == 404
    assert superadmin.delete(f"{BASE}/{other.user_id}").status_code == 404


# The database keeps a location safe whoever writes: nobody changes their
# own staff role, and a location always keeps an admin. (A new location of
# its own, so exactly one admin there.)
def test_database_rules_for_staff_roles(api: Api):
    code = f"loc-{uuid.uuid4().hex[:8]}"
    [(location_id,)] = api.sql(
        "INSERT INTO tenancy.locations (tenant_id, code, name, address_line_1, suburb, state, postcode) "
        "SELECT t.id, :code, 'Test centre', '1 Test Street', 'Brisbane City', 'QLD', '4000' "
        "FROM tenancy.tenants t WHERE t.code = 'tenant1' RETURNING id::text",
        code=code,
    )
    only_admin = api.new_staff(role="admin", pin=None, location=code)
    staff = api.new_staff(pin=None, location=code)

    def as_staff(statement: str, **params):
        with SessionLocal() as db:
            db.execute(
                text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
                {"u": staff.user_id, "l": location_id},
            )
            db.execute(text(statement), params)
            db.commit()

    with pytest.raises(Exception, match="own role"):
        as_staff(
            "DELETE FROM auth.location_user_roles WHERE user_id = CAST(:u AS uuid) AND location_id = CAST(:l AS uuid)",
            u=staff.user_id,
            l=location_id,
        )

    with pytest.raises(Exception, match="no admin"):
        as_staff(
            "DELETE FROM auth.location_user_roles WHERE user_id = CAST(:u AS uuid) AND location_id = CAST(:l AS uuid)",
            u=only_admin.user_id,
            l=location_id,
        )


# Families and staff (on the website) can't see the staff list.
def test_staff_list_is_for_admins(api: Api, customer):
    staff = api.new_staff(pin=None)

    assert customer.client.get(f"{BASE}/").status_code == 403
    assert staff.client.get(f"{BASE}/").status_code == 403
