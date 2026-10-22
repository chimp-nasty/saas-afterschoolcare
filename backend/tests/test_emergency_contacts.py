"""
Emergency contacts: each family has exactly one (a name, a phone and how
they're related), and can't book without it. Its phone is a valid
Australian number that isn't the parent's own, and needn't be unique. It
has nothing to do with pickup people. Only the family changes it; admins
see it on the family's page and staff at the staff kiosk.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from tests.factories import Api, new_phone


PROFILE = "/customer/v1/profile"
KIOSK = "/staff-kiosk/v1/location1"


def _user_id(api: Api, email: str) -> str:
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=email)

    return user_id


# A family saves their emergency contact; the phone is stored as 10 digits.
def test_save_emergency_contact(customer):
    response = customer.client.patch(
        PROFILE,
        json={
            "emergency_contact_name": " Sam Lee ",
            "emergency_contact_phone": "+61 411 222 333",
            "emergency_contact_relation": "family_friend",
        },
    )
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert (data["emergency_contact_name"], data["emergency_contact_phone"], data["emergency_contact_relation"]) == (
        "Sam Lee",
        "0411222333",
        "family_friend",
    )


# Without an emergency contact a family can't book, and is told it's missing.
def test_cannot_book_without_emergency_contact(api: Api, customer):
    child = api.new_child(customer)
    customer.client.patch(PROFILE, json={"emergency_contact_name": None})

    response = api.book(customer, {child["id"]: [api.service_day()]})

    assert response.status_code == 400
    assert "Missing: emergency_contact" in response.json()["msg"]


# The contact's phone must be a valid Australian number and not the
# parent's own; another family may list the same contact.
def test_emergency_phone_rules(api: Api, customer):
    assert customer.client.patch(PROFILE, json={"emergency_contact_phone": "12345"}).status_code == 422

    response = customer.client.patch(PROFILE, json={"emergency_contact_phone": customer.phone})
    assert response.status_code == 400
    assert response.json()["msg"] == "Your emergency contact needs a different phone number from yours"

    shared = new_phone()
    other = api.new_customer()
    assert customer.client.patch(PROFILE, json={"emergency_contact_phone": shared}).status_code == 200
    assert other.client.patch(PROFILE, json={"emergency_contact_phone": shared}).status_code == 200


# The parent can't change their own phone to their contact's number either.
def test_parent_phone_cannot_match_contact(customer):
    contact_phone = customer.client.get(PROFILE).json()["data"]["emergency_contact_phone"]

    assert customer.client.patch(PROFILE, json={"phone": contact_phone}).status_code == 400


# "Other" needs the family's own words; choosing a listed relation clears them.
def test_other_relation_needs_wording(customer):
    assert customer.client.patch(PROFILE, json={"emergency_contact_relation": "other"}).status_code == 400

    response = customer.client.patch(
        PROFILE, json={"emergency_contact_relation": "other", "emergency_contact_relation_other": "Godparent"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["emergency_contact_relation_other"] == "Godparent"

    data = customer.client.patch(PROFILE, json={"emergency_contact_relation": "neighbour"}).json()["data"]
    assert (data["emergency_contact_relation"], data["emergency_contact_relation_other"]) == ("neighbour", None)


# The emergency contact isn't a pickup person: saving one adds no one to
# the family's pickup list.
def test_not_a_pickup_person(api: Api, customer):
    customer.client.patch(PROFILE, json={"emergency_contact_phone": new_phone()})

    [(count,)] = api.sql(
        "SELECT count(*) FROM public.authorized_pickup_persons p JOIN auth.users u ON u.id = p.user_id "
        "WHERE u.email = :e",
        e=customer.email,
    )
    assert count == 1  # only the account holder


# Admins see the contact on the family's page but can't change it: the
# admin form ignores it, and the database refuses an admin session.
def test_admins_read_but_cannot_change(api: Api, admin, customer):
    user_id = _user_id(api, customer.email)

    family = admin.get(f"/families/v1/{user_id}").json()["data"]
    assert (family["emergency_contact_name"], family["emergency_contact_relation"]) == ("Robin Contact", "grandparent")

    response = admin.patch(f"/families/v1/{user_id}", json={"emergency_contact_name": "Changed", "suburb": "Toowong"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["emergency_contact_name"] == "Robin Contact"

    [(admin_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = 't1user@test.com'")
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )

    with SessionLocal() as db:
        db.execute(
            text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
            {"u": admin_id, "l": location_id},
        )

        with pytest.raises(IntegrityError, match="Only the family"):
            db.execute(
                text("UPDATE public.customer_profile SET emergency_contact_name = 'Changed' WHERE user_id = :u"),
                {"u": user_id},
            )


# Staff on shift see the family's emergency contact on the staff kiosk's roll.
def test_staff_see_it_at_the_kiosk(api: Api, admin, customer):
    tablet = api.kiosk(admin, "staff")
    staff = api.new_staff()
    headers = {"X-Kiosk-Staff": staff.user_id, "X-Kiosk-Pin": staff.pin}
    assert tablet.post(f"{KIOSK}/shift", json={"action": "start"}, headers=headers).status_code == 200

    child = api.new_child(customer)
    api.booking_today(customer, child["id"])

    response = tablet.get(f"{KIOSK}/roll", headers=headers)
    assert response.status_code == 200, response.text

    [entry] = [e for e in response.json()["data"]["entries"] if e["child_id"] == child["id"]]
    assert (entry["emergency_contact_name"], entry["emergency_contact_relation"]) == ("Robin Contact", "grandparent")
    assert entry["emergency_contact_phone"]
