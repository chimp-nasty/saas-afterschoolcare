"""
The portal split (docs/portals.md): staff manage themselves, admins manage
the business, operations happen at the staff kiosk. A staff login on the
website reaches nothing about children, families, medical records,
bookings or attendance, and the database refuses it too, not just the
routes. Admins keep it on the website; staff get it only at the kiosk.
"""

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from tests.factories import Api


def _session(api: Api, user_id: str, *, kiosk: bool = False):
    """A database session as this user at tenant1/location1, on the web or at the kiosk."""
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )
    db = SessionLocal()
    db.execute(
        text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
        {"u": user_id, "l": location_id},
    )

    if kiosk:
        db.execute(text("SELECT set_config('app.channel', 'kiosk', true)"))

    return db


@pytest.fixture
def booked_child(api: Api, customer):
    child = api.new_child(customer)

    return child, api.booking_today(customer, child["id"])


# A staff login on the website can't reach any family's data.
@pytest.mark.parametrize(
    "path",
    [
        "/children/v1/",
        "/medical-reviews/v1/",
        "/attendance/v1/roll",
        "/attendance/v1/board",
        "/pickups/v1/",
        "/booking/v1/",
        "/customer/v1/profile",
        "/kiosk-devices/v1/",
    ],
)
def test_staff_web_login_reaches_no_family_data(api: Api, path):
    staff = api.new_staff()

    assert staff.client.get(path).status_code == 403


# Even past the routes, the database shows a staff login on the website no
# children, and the same staff member at the kiosk sees them.
def test_database_hides_family_data_from_staff_on_the_web(api: Api, booked_child):
    staff = api.new_staff(pin=None)
    child, _ = booked_child

    with _session(api, staff.user_id) as db:
        assert db.execute(text("SELECT count(*) FROM public.child_profile WHERE id = :id"), {"id": child["id"]}).scalar_one() == 0

    with _session(api, staff.user_id, kiosk=True) as db:
        assert db.execute(text("SELECT count(*) FROM public.child_profile WHERE id = :id"), {"id": child["id"]}).scalar_one() == 1


# The roll function itself returns nothing to a staff login on the website.
def test_roll_function_refuses_staff_on_the_web(api: Api, booked_child):
    staff = api.new_staff(pin=None)

    with _session(api, staff.user_id) as db:
        rows = db.execute(text(
            "SELECT * FROM public.attendance_roll(current_setting('app.location_id')::uuid, "
            "(now() AT TIME ZONE 'Australia/Brisbane')::date)"
        )).all()

    assert rows == []


# Admins keep the business on the website: children and the run sheet.
def test_admin_web_login_keeps_family_data(admin, booked_child):
    _, booking_id = booked_child

    assert admin.get("/children/v1/").status_code == 200
    assert booking_id in [e["booking_id"] for e in admin.get("/attendance/v1/roll").json()["data"]["entries"]]


# Admins see the run sheet as the staff kiosk shows it (sessions with their
# places, and who signed each child in and out), read-only.
def test_admin_sees_the_kiosk_run_sheet(admin, customer, booked_child):
    _, booking_id = booked_child

    response = admin.get("/attendance/v1/board")
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    [entry] = [e for e in data["entries"] if e["booking_id"] == booking_id]
    assert [s for s in data["sessions"] if s["service_name"] == entry["service_name"]]
    assert customer.client.get("/attendance/v1/board").status_code == 403


# Medical approval is an admin's: staff can't decide a review, even at the
# kiosk channel in the database.
def test_staff_cannot_decide_medical_reviews(api: Api, customer):
    staff = api.new_staff(pin=None)
    child = api.new_child(customer, medical_info="Asthma")

    with _session(api, staff.user_id, kiosk=True) as db:
        db.execute(
            text("UPDATE public.child_medical_state SET review_status = 'approved' WHERE child_id = :id"),
            {"id": child["id"]},
        )
        db.commit()

    [(status,)] = api.sql("SELECT review_status::text FROM public.child_medical_state WHERE child_id = :id", id=child["id"])
    assert status == "pending"


# An admin on the website can't record attendance or approve a pickup
# person: those happen only at the staff kiosk.
def test_admin_web_cannot_do_physical_actions(api: Api, customer, booked_child):
    _, booking_id = booked_child
    [(admin_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = 't1user@test.com'")
    [(holder,)] = api.sql(
        "SELECT id::text FROM public.authorized_pickup_persons WHERE lower(email) = lower(:email)",
        email=customer.email,
    )

    with _session(api, admin_id) as db, pytest.raises(Exception, match="kiosk"):
        db.execute(text("INSERT INTO public.attendance_records (booking_id, signed_in_at) VALUES (:b, now())"), {"b": booking_id})

    with _session(api, admin_id) as db:
        db.execute(text("UPDATE public.authorized_pickup_persons SET staff_approved_at = now() WHERE id = :id"), {"id": holder})
        db.commit()

    [(approved,)] = api.sql("SELECT staff_approved_at IS NOT NULL FROM public.authorized_pickup_persons WHERE id = :id", id=holder)
    assert approved is False
