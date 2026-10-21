"""
The website side of the staff kiosk: anyone who works at the centre sets
their own staff PIN in their staff portal (after re-entering their
password), and admins see the day's run sheet read-only, with each booked
family's pickup list for when the kiosks are down (docs/portals.md).
"""

from tests.factories import Api


# An admin sets a PIN with their password, and can see that it's set
# (never the PIN itself).
def test_staff_set_their_pin(admin):
    response = admin.put("/staff-pin/v1/", json={"password": "123", "pin": "2468"})
    assert response.status_code == 200, response.text

    status = admin.get("/staff-pin/v1/").json()["data"]
    assert status["is_set"] is True
    assert status["is_locked"] is False
    assert "pin" not in status


# The wrong password, or a PIN that isn't 4 digits, is refused.
def test_staff_pin_needs_password_and_four_digits(admin):
    assert admin.put("/staff-pin/v1/", json={"password": "wrong", "pin": "2468"}).status_code == 400
    assert admin.put("/staff-pin/v1/", json={"password": "123", "pin": "24a8"}).status_code == 400


# A staff-role login sets their own PIN in the staff portal.
def test_staff_role_sets_their_pin(api: Api):
    staff = api.new_staff(pin=None)

    assert staff.client.put("/staff-pin/v1/", json={"password": "Password123", "pin": "2468"}).status_code == 200
    assert staff.client.get("/staff-pin/v1/").json()["data"]["is_set"] is True


# Families don't have staff PINs.
def test_customers_have_no_staff_pin(customer):
    assert customer.client.get("/staff-pin/v1/").status_code == 403
    assert customer.client.put("/staff-pin/v1/", json={"password": "Password123", "pin": "2468"}).status_code == 403


# Admins see today's run sheet on the website, with the booked family's pickup
# list and who's approved.
def test_roll_on_the_website(api: Api, admin, customer):
    child = api.new_child(customer)
    booking_id = api.booking_today(customer, child["id"])

    response = admin.get("/attendance/v1/roll")
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    [entry] = [e for e in data["entries"] if e["booking_id"] == booking_id]
    [family] = [f for f in data["families"] if f["family_user_id"] == entry["family_user_id"]]

    assert [p["relation"] for p in family["pickups"]] == ["account_holder"]
    assert family["pickups"][0]["staff_approved_at"] is None


# Families can't see the centre's roll.
def test_customers_cannot_see_the_roll(customer):
    assert customer.client.get("/attendance/v1/roll").status_code == 403


# Another tenant's admins don't see this location's children on their roll.
def test_roll_is_per_location(api: Api, tenant2_admin, customer):
    child = api.new_child(customer)
    booking_id = api.booking_today(customer, child["id"])

    entries = tenant2_admin.get("/attendance/v1/roll").json()["data"]["entries"]

    assert booking_id not in [e["booking_id"] for e in entries]
