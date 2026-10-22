"""
Families (Admin › Families, slice 4-4): admins and superadmins find a
family at their centre, see its page (details, children, pickup people),
correct its phone and address, and see its bookings, attendance history and
payments. Families and staff can't; another centre's families aren't found.
"""

import pytest

from tests.factories import Api, new_phone


BASE = "/families/v1"


def _family_id(api: Api, customer) -> str:
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    return user_id


def _search(client, q: str) -> list[dict]:
    response = client.get(f"{BASE}/", params={"q": q})
    assert response.status_code == 200, response.text

    return response.json()["data"]


# An admin finds a family by a child's name, the parent's name, their
# email or their phone; another centre's family isn't found.
def test_search(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    api.new_child(customer, first_name="Wilhelmina")
    other = api.new_customer(tenant="tenant2", location="location2")
    api.new_child(other, first_name="Wilhelmina")

    by_child = _search(admin, "wilhel")
    assert [f["user_id"] for f in by_child] == [user_id]
    assert by_child[0]["children"] == "Wilhelmina"

    assert user_id in [f["user_id"] for f in _search(admin, customer.email[:12])]
    assert user_id in [f["user_id"] for f in _search(admin, customer.phone[-6:])]


# A search needs at least 2 characters.
def test_search_needs_two_characters(admin):
    assert admin.get(f"{BASE}/", params={"q": "a"}).status_code == 422


# The family page has the parent's details, children with their medical
# status, and the pickup list with ID status.
def test_family_page(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer, allergy_info="Peanuts")

    response = admin.get(f"{BASE}/{user_id}")
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert (data["email"], data["phone"], data["postcode"]) == (customer.email, customer.phone, "4000")
    [listed] = [c for c in data["children"] if c["id"] == child["id"]]
    assert listed["review_status"] == "pending"
    assert [p["relation"] for p in data["pickups"]] == ["account_holder"]


# An admin corrects a family's phone and address. The family's own place
# on their pickup list follows the new phone, so it needs approving again.
def test_correct_details(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    api.sql(
        "UPDATE public.authorized_pickup_persons SET staff_approved_at = now() WHERE lower(email) = lower(:e)",
        e=customer.email,
    )
    phone = new_phone()

    response = admin.patch(f"{BASE}/{user_id}", json={"phone": phone, "address_line_1": "2 New Street"})
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert (data["phone"], data["address_line_1"]) == (phone, "2 New Street")
    [holder] = data["pickups"]
    assert holder["phone"] == phone
    assert holder["staff_approved_at"] is None


# Bookings: from a month back to three months ahead by default, and any
# awaiting payment whatever the date.
def test_bookings(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    today = api.booking_today(customer, api.new_child(customer)["id"])
    far = api.new_child(customer)
    paid = api.book(customer, {far["id"]: [api.service_day()]}).json()["data"]
    api.webhook("checkout.session.completed", api.session_id(paid["checkout_url"]))
    [(far_paid,)] = api.sql("SELECT id::text FROM public.bookings WHERE booking_group_id = :g", g=paid["booking_group_id"])
    unpaid = api.book(customer, {far["id"]: [api.service_day()]}).json()["data"]
    [(far_unpaid,)] = api.sql("SELECT id::text FROM public.bookings WHERE booking_group_id = :g", g=unpaid["booking_group_id"])

    listed = {b["id"]: b for b in admin.get(f"{BASE}/{user_id}/bookings").json()["data"]}

    assert listed[today]["payment_status"] == "PAID"
    assert listed[today]["is_refundable_by_admin"] is True
    assert far_unpaid in listed
    assert far_paid not in listed


# Attendance history shows who signed each child in and out, and who
# collected them.
def test_attendance_history(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    booking_id = api.booking_today(customer, api.new_child(customer)["id"])
    staff = api.new_staff()
    tablet = api.kiosk(admin, "staff")
    headers = {"X-Kiosk-Staff": staff.user_id, "X-Kiosk-Pin": staff.pin}
    tablet.post("/staff-kiosk/v1/location1/shift", json={"action": "start"}, headers=headers)
    [(holder,)] = api.sql(
        "SELECT id::text FROM public.authorized_pickup_persons WHERE lower(email) = lower(:e)", e=customer.email
    )
    tablet.post("/staff-kiosk/v1/location1/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=headers)
    tablet.post("/staff-kiosk/v1/location1/sign", json={"booking_id": booking_id, "action": "in"}, headers=headers)
    tablet.post(
        "/staff-kiosk/v1/location1/sign",
        json={"booking_id": booking_id, "action": "out", "collected_by_pickup_person_id": holder},
        headers=headers,
    )

    [entry] = [e for e in admin.get(f"{BASE}/{user_id}/attendance").json()["data"] if e["booking_id"] == booking_id]

    assert entry["signed_in_by"] == "Staff M."
    assert entry["signed_out_by"] == "Staff M."
    assert entry["collected_by"]
    assert entry["collector_id_sighted"] is True


# Payments list each checkout and what's been refunded from it.
def test_payments(api: Api, admin, customer, fake_stripe):
    user_id = _family_id(api, customer)
    booking_id = api.booking_today(customer, api.new_child(customer)["id"])

    [payment] = admin.get(f"{BASE}/{user_id}/payments").json()["data"]
    assert (payment["stripe_status"], payment["bookings"], payment["refunded_cents"]) == ("SUCCEEDED", 1, 0)

    assert admin.post("/refunds/v1/", json={"booking_id": booking_id}).status_code == 201
    [stripe_refund_id] = [rid for rid, r in fake_stripe.state.refunds.items() if r["metadata"]["booking_id"] == booking_id]
    api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded")

    [payment] = admin.get(f"{BASE}/{user_id}/payments").json()["data"]
    assert payment["refunded_cents"] == payment["total_cents"]


# Families and staff (on the website) can't search families or open one.
@pytest.mark.parametrize("who", ["customer", "staff"])
def test_only_admins(api: Api, customer, who):
    client = customer.client if who == "customer" else api.new_staff(pin=None).client

    assert client.get(f"{BASE}/", params={"q": "ab"}).status_code == 403
    assert client.get(f"{BASE}/{_family_id(api, customer)}").status_code == 403


# Superadmins have it too, and another centre's family isn't found.
def test_superadmins_and_other_centres(api: Api, superadmin, customer):
    assert superadmin.get(f"{BASE}/{_family_id(api, customer)}").status_code == 200

    other = api.new_customer(tenant="tenant2", location="location2")
    assert superadmin.get(f"{BASE}/{_family_id(api, other)}").status_code == 404
