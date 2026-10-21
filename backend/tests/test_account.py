"""
Your own account (docs/portals.md): everyone who logs in can see their
details and where they work, read-only, and change their password after
re-entering the current one. A "password changed" email follows.
"""

from app.integrations.email.messages import PasswordChangedEmail
from tests.factories import PASSWORD, Api


# Staff see their own details and their role at this location, nothing
# about anyone else.
def test_staff_see_their_account(api: Api):
    staff = api.new_staff(pin=None)

    response = staff.client.get("/account/v1/")
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert data["email"] == staff.email
    assert [(r["location_code"], r["role_code"]) for r in data["roles"]] == [("location1", "staff")]


# Families see their own account too.
def test_customers_see_their_account(customer):
    data = customer.client.get("/account/v1/").json()["data"]

    assert data["email"] == customer.email
    assert [r["role_code"] for r in data["roles"]] == ["customer"]


# Roles at another business's locations aren't shown: only this tenant's.
def test_other_tenants_roles_are_not_shown(api: Api):
    staff = api.new_staff(pin=None)
    api.sql(
        "INSERT INTO auth.location_user_roles (user_id, location_id, role_id) "
        "SELECT CAST(:user_id AS uuid), l.id, r.id "
        "FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id, auth.roles r "
        "WHERE t.code = 'tenant2' AND l.code = 'location2' AND r.code = 'staff'",
        user_id=staff.user_id,
    )

    data = staff.client.get("/account/v1/").json()["data"]

    assert [r["location_code"] for r in data["roles"]] == ["location1"]


# Changing your password needs the current one; then the new one logs in,
# the old one doesn't, and a "password changed" email is sent.
def test_change_password(api: Api, customer, sent_emails):
    response = customer.client.post(
        "/account/v1/password",
        json={"current_password": PASSWORD, "new_password": "NewPassword456"},
    )
    assert response.status_code == 200, response.text

    assert api.login(customer.email, "NewPassword456").get("/account/v1/").status_code == 200
    assert api.client().post(
        "/auth/v1/login/location1",
        json={"email": customer.email, "password": PASSWORD},
    ).status_code == 401
    assert [m.to_email for m in sent_emails(PasswordChangedEmail)] == [customer.email]


# The wrong current password changes nothing and sends nothing.
def test_change_password_needs_the_current_one(api: Api, sent_emails):
    staff = api.new_staff(pin=None)

    response = staff.client.post(
        "/account/v1/password",
        json={"current_password": "wrong", "new_password": "NewPassword456"},
    )

    assert response.status_code == 400
    assert api.login(staff.email, PASSWORD).get("/account/v1/").status_code == 200
    assert sent_emails(PasswordChangedEmail) == []


# A new password must be at least 8 characters.
def test_new_password_too_short(customer):
    response = customer.client.post(
        "/account/v1/password",
        json={"current_password": PASSWORD, "new_password": "short"},
    )

    assert response.status_code == 422


# Not logged in: no account.
def test_account_needs_a_login(api: Api):
    assert api.client().get("/account/v1/").status_code == 401
