"""
Whole days at the centre (docs/portals.md, step 5): the three portals (the
staff portal, the admin portal and the staff kiosk) and the family kiosk,
used together in the order real people use them. Each test is one story;
the unit-style tests next to this file check each rule on its own.
"""

from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from app.integrations.email.messages import KioskPinEmail, RefundConfirmationEmail
from app.kiosk import tokens
from app.kiosk.dependencies import PIN_HEADER, STAFF_HEADER
from tests.factories import Api, Customer, StaffMember


STAFF = "/staff-kiosk/v1/location1"
FAMILY = "/kiosk/v1/location1"


# ---------------------------------------------------------------------------
# The centre's two tablets, and the people at them
# ---------------------------------------------------------------------------

@pytest.fixture
def staff_tablet(api: Api, admin):
    return api.kiosk(admin, "staff")


@pytest.fixture
def family_tablet(api: Api, admin):
    return api.kiosk(admin, "family")


def _as(staff: StaffMember, pin: str | None = None) -> dict:
    return {STAFF_HEADER: staff.user_id, PIN_HEADER: pin or staff.pin}


def _on_shift(api: Api, tablet, **staff_options) -> StaffMember:
    """A staff member who set their PIN in their staff portal and clocked in."""
    member = api.new_staff(**staff_options)
    response = tablet.post(f"{STAFF}/shift", json={"action": "start"}, headers=_as(member))
    assert response.status_code == 200, response.text

    return member


def _bulk(tablet, staff: StaffMember, action: str, booking_ids: list[str], **body):
    return tablet.post(
        f"{STAFF}/bulk",
        json={"action": action, "booking_ids": booking_ids, **body},
        headers=_as(staff),
    )


def _sign(tablet, staff: StaffMember, **body):
    return tablet.post(f"{STAFF}/sign", json=body, headers=_as(staff))


def _row(tablet, booking_id: str, date: str | None = None) -> dict:
    """A child's row on the run sheet, as the tablet shows it before any PIN."""
    params = {"date": date} if date else {}
    [row] = [e for e in tablet.get(f"{STAFF}/board", params=params).json()["data"]["entries"] if e["booking_id"] == booking_id]

    return row


def _holder(api: Api, customer: Customer) -> str:
    """The account holder's own place on their family's pickup list."""
    [(person_id,)] = api.sql(
        "SELECT id::text FROM public.authorized_pickup_persons WHERE lower(email) = lower(:email)",
        email=customer.email,
    )

    return person_id


def _family_kiosk_login(tablet, customer: Customer, sent_emails) -> str:
    """The parent logs in at the family kiosk with the emailed PIN and chooses their own."""
    [setup_pin] = [m.pin for m in sent_emails(KioskPinEmail) if m.to_email == customer.email][-1:]
    response = tablet.post(f"{FAMILY}/login", json={"phone": customer.phone, "pin": setup_pin})
    assert response.status_code == 200, response.text

    response = tablet.post(
        f"{FAMILY}/pin",
        json={"new_pin": "2468"},
        headers={tokens.SESSION_HEADER: response.json()["data"]["session"]["token"]},
    )
    assert response.status_code == 200, response.text

    return response.json()["data"]["token"]


def _family_sign(tablet, token: str, booking_id: str, action: str):
    return tablet.post(
        f"{FAMILY}/sign",
        json={"booking_id": booking_id, "action": action},
        headers={tokens.SESSION_HEADER: token},
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

# A new family's first day: they book and pay; staff sign the session's
# arrivals in together; the parent can't sign out at the family kiosk until
# staff check their ID, then can; the admin's run sheet shows the whole day.
def test_new_familys_first_day(api: Api, admin, staff_tablet, family_tablet, customer, sent_emails):
    child = api.new_child(customer)
    booking_id = api.booking_today(customer, child["id"])
    staff = _on_shift(api, staff_tablet)

    assert _bulk(staff_tablet, staff, "sign_in", [booking_id]).status_code == 200
    assert _row(staff_tablet, booking_id)["signed_in_by"] == "Staff M."

    token = _family_kiosk_login(family_tablet, customer, sent_emails)
    refused = _family_sign(family_tablet, token, booking_id, "out")
    assert refused.status_code == 409
    assert "staff member" in refused.json()["msg"]

    checked = staff_tablet.post(
        f"{STAFF}/check-id",
        json={"pickup_person_id": _holder(api, customer), "id_seen": True},
        headers=_as(staff),
    )
    assert checked.status_code == 200, checked.text

    response = _family_sign(family_tablet, token, booking_id, "out")
    assert response.status_code == 200, response.text

    [row] = [e for e in admin.get("/attendance/v1/board").json()["data"]["entries"] if e["booking_id"] == booking_id]
    assert row["signed_in_by"] == "Staff M."
    assert row["signed_out_at"] is not None
    assert row["collected_by"]
    assert row["collector_id_sighted"] is True


# A medical change mid-term: the family edits an approved allergy, and the
# kiosk shows it's waiting for review (and the plan as NEW) while staff
# still see the details; staff tick the plan printed; once the admin
# approves, the kiosk says so and the printed tick is kept.
def test_medical_change_mid_term(api: Api, admin, staff_tablet, customer):
    child = api.new_child(customer, allergy_info="Peanuts")
    plan = api.upload_document(customer, child["id"], document_type="allergy_anaphylaxis_plan")
    assert admin.post(f"/medical-reviews/v1/{child['id']}", json={"decision": "approved"}).status_code == 200
    booking_id = api.booking_today(customer, child["id"])
    staff = _on_shift(api, staff_tablet)

    response = customer.client.patch(f"/children/v1/{child['id']}", json={"allergy_info": "Peanuts and tree nuts"})
    assert response.status_code == 200, response.text

    assert _row(staff_tablet, booking_id)["has_medical"] is True
    medical = staff_tablet.get(f"{STAFF}/children/{child['id']}/medical", headers=_as(staff)).json()["data"]
    assert medical["review_status"] == "pending"
    assert medical["allergy_info"] == "Peanuts and tree nuts"

    def folder_entry():
        [entry] = [p for p in staff_tablet.get(f"{STAFF}/action-plans", headers=_as(staff)).json()["data"]
                   if p["document_id"] == plan["id"]]
        return entry

    assert folder_entry()["is_new"] is True
    assert staff_tablet.put(f"{STAFF}/documents/{plan['id']}/printed", json={"printed": True}, headers=_as(staff)).status_code == 200

    assert admin.post(f"/medical-reviews/v1/{child['id']}", json={"decision": "approved"}).status_code == 200

    medical = staff_tablet.get(f"{STAFF}/children/{child['id']}/medical", headers=_as(staff)).json()["data"]
    assert medical["review_status"] == "approved"
    assert folder_entry()["printed_by"] == "Staff M."
    # Still new: uploaded in the last 7 days.
    assert folder_entry()["is_new"] is True


# Brothers and sisters through a school day: signed in to before school care
# and sent to school together; signed in from school to after school care;
# collected together by their parent, approved without ID, which the
# records say.
def test_siblings_school_day(api: Api, admin, staff_tablet, customer):
    children = [api.new_child(customer) for _ in range(2)]
    before = [api.booking_today(customer, c["id"], service="before_school_care") for c in children]
    after = [api.booking_today(customer, c["id"]) for c in children]
    staff = _on_shift(api, staff_tablet)

    assert _bulk(staff_tablet, staff, "sign_in", before).status_code == 200
    assert _bulk(staff_tablet, staff, "to_school", before).status_code == 200
    for booking_id in before:
        assert _row(staff_tablet, booking_id)["sent_to_school"] is True

    holder = _holder(api, customer)
    assert _bulk(staff_tablet, staff, "sign_in", after).status_code == 200
    assert staff_tablet.post(
        f"{STAFF}/check-id", json={"pickup_person_id": holder, "id_seen": False}, headers=_as(staff)
    ).status_code == 200
    assert _bulk(staff_tablet, staff, "sign_out", after, collected_by_pickup_person_id=holder).status_code == 200

    roll = admin.get("/attendance/v1/roll").json()["data"]["entries"]
    for booking_id in after:
        [entry] = [e for e in roll if e["booking_id"] == booking_id]
        assert entry["collected_by"]
        assert entry["collector_id_sighted"] is False


# An aunt not on the list collects one child (a one-off release, confirmed
# with the PIN), and another staff member signs the wrong child out and
# undoes it; each action is recorded against the right person.
def test_one_off_release_and_a_correction(api: Api, staff_tablet, customer):
    released = api.booking_today(customer, api.new_child(customer)["id"])
    mistaken = api.booking_today(customer, api.new_child(customer)["id"])
    first = _on_shift(api, staff_tablet)
    second = _on_shift(api, staff_tablet, pin="3691")
    holder = _holder(api, customer)
    staff_tablet.post(f"{STAFF}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(first))
    _bulk(staff_tablet, first, "sign_in", [released, mistaken])

    response = _bulk(
        staff_tablet, first, "sign_out", [released],
        released_to_name="Pat Lee", release_note="Phoned the account holder 5:40pm; licence checked",
    )
    assert response.status_code == 200, response.text

    assert _bulk(staff_tablet, second, "sign_out", [mistaken], collected_by_pickup_person_id=holder).status_code == 200
    undo = staff_tablet.post(f"{STAFF}/undo", json={"booking_id": mistaken, "step": "sign_out"}, headers=_as(second))
    assert undo.status_code == 200, undo.text

    assert _row(staff_tablet, released)["released_to"] == "Pat L."
    assert _row(staff_tablet, mistaken)["signed_out_at"] is None
    [(released_by,)] = api.sql(
        "SELECT signed_out_by_user_id::text FROM public.attendance_records WHERE booking_id = CAST(:b AS uuid)",
        b=released,
    )
    assert released_by == first.user_id


# A staff member forgets to clock out; the next day they can't act until
# they clock in, which asks when they left and closes yesterday's shift.
def test_forgotten_clock_out_next_day(api: Api, staff_tablet, customer):
    staff = _on_shift(api, staff_tablet)
    api.sql(
        "UPDATE public.staff_shifts SET started_at = started_at - interval '1 day' "
        "WHERE user_id = CAST(:id AS uuid) AND ended_at IS NULL",
        id=staff.user_id,
    )
    [(started_at,)] = api.sql(
        "SELECT started_at FROM public.staff_shifts WHERE user_id = CAST(:id AS uuid) AND ended_at IS NULL",
        id=staff.user_id,
    )
    booking_id = api.booking_today(customer, api.new_child(customer)["id"])

    assert _sign(staff_tablet, staff, booking_id=booking_id, action="in").status_code == 403

    left = started_at + timedelta(hours=4)
    response = staff_tablet.post(
        f"{STAFF}/shift",
        json={"action": "start", "previous_shift_ended_at": left.isoformat()},
        headers=_as(staff),
    )
    assert response.status_code == 200, response.text

    assert _sign(staff_tablet, staff, booking_id=booking_id, action="in").status_code == 200
    [(ended_at,)] = api.sql(
        "SELECT ended_at FROM public.staff_shifts WHERE user_id = CAST(:id AS uuid) AND started_at = :s",
        id=staff.user_id,
        s=started_at,
    )
    assert ended_at == left


# The admin turns kiosk times on: too early, neither kiosk signs a child in;
# around the session both do; turned off, any time works again.
def test_kiosk_times_from_on_to_off(api: Api, admin, staff_tablet, family_tablet, customer, sent_emails, service_times):
    children = [api.new_child(customer) for _ in range(3)]
    bookings = [api.booking_today(customer, c["id"]) for c in children]
    staff = _on_shift(api, staff_tablet)
    token = _family_kiosk_login(family_tablet, customer, sent_emails)

    assert admin.put("/kiosk-devices/v1/settings", json={"enforce_service_times": True}).status_code == 200
    service_times(3)
    assert _family_sign(family_tablet, token, bookings[0], "in").status_code == 409
    assert _sign(staff_tablet, staff, booking_id=bookings[1], action="in").status_code == 409

    service_times(1)
    response = _family_sign(family_tablet, token, bookings[0], "in")
    assert response.status_code == 200, response.text
    assert _sign(staff_tablet, staff, booking_id=bookings[1], action="in").status_code == 200

    assert admin.put("/kiosk-devices/v1/settings", json={"enforce_service_times": False}).status_code == 200
    service_times(3)
    assert _sign(staff_tablet, staff, booking_id=bookings[2], action="in").status_code == 200


# A refund past the family's cutoff: the family can't, an admin on shift
# refunds it at the kiosk, and once Stripe confirms, the booking is
# cancelled and refunded, its place is free again, the family's bookings
# say so, and the family is emailed.
def test_kiosk_refund_flows_everywhere(api: Api, staff_tablet, customer, fake_stripe, sent_emails):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)
    [(family_user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)
    [(service_date,)] = api.sql(
        "SELECT d.service_date::text FROM public.bookings b JOIN public.location_service_days d "
        "ON d.id = b.location_service_day_id WHERE b.id = CAST(:b AS uuid)",
        b=booking_id,
    )
    admin_member = _on_shift(api, staff_tablet, role="admin")

    assert customer.client.post("/refunds/v1/", json={"booking_id": booking_id}).status_code == 409

    def places_left() -> int:
        sessions = staff_tablet.get(f"{STAFF}/board", params={"date": service_date}).json()["data"]["sessions"]
        [session] = [s for s in sessions if s["service_code"] == "after_school_care"]
        return session["places_left"]

    before = places_left()

    response = staff_tablet.post(f"{STAFF}/refunds", json={"booking_id": booking_id}, headers=_as(admin_member))
    assert response.status_code == 201, response.text

    [stripe_refund_id] = [rid for rid, r in fake_stripe.state.refunds.items() if r["metadata"]["booking_id"] == booking_id]
    assert api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded").status_code == 200

    [booking] = [
        b for b in staff_tablet.get(f"{STAFF}/families/{family_user_id}/bookings", headers=_as(admin_member)).json()["data"]
        if b["id"] == booking_id
    ]
    assert (booking["booking_status"], booking["payment_status"]) == ("CANCELLED", "REFUNDED")
    assert places_left() == before + 1
    assert [m.to_email for m in sent_emails(RefundConfirmationEmail)] == [customer.email]


# A staff member's whole day at the kiosk leaves their website login as it
# was: only their own account. What they did shows on the admin's run sheet
# under their short name, and the database still won't let an admin on the
# website sign a child in.
def test_portal_split_through_a_day(api: Api, admin, staff_tablet, customer):
    child = api.new_child(customer, allergy_info="Peanuts")
    assert admin.post(f"/medical-reviews/v1/{child['id']}", json={"decision": "approved"}).status_code == 200
    booking_id = api.booking_today(customer, child["id"])
    staff = _on_shift(api, staff_tablet)

    assert _sign(staff_tablet, staff, booking_id=booking_id, action="in").status_code == 200
    assert staff_tablet.get(f"{STAFF}/children/{child['id']}/medical", headers=_as(staff)).status_code == 200

    for path in ("/children/v1/", "/attendance/v1/board", "/booking/v1/", "/medical-reviews/v1/"):
        assert staff.client.get(path).status_code == 403, path
    assert staff.client.get("/account/v1/").status_code == 200

    [row] = [e for e in admin.get("/attendance/v1/board").json()["data"]["entries"] if e["booking_id"] == booking_id]
    assert row["signed_in_by"] == "Staff M."

    other = api.booking_today(customer, api.new_child(customer)["id"])
    [(admin_id, location_id)] = api.sql(
        "SELECT u.id::text, lur.location_id::text FROM auth.users u "
        "JOIN auth.location_user_roles lur ON lur.user_id = u.id WHERE u.email = 't1user@test.com' LIMIT 1"
    )
    with SessionLocal() as db, pytest.raises(Exception, match="kiosk"):
        db.execute(
            text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
            {"u": admin_id, "l": location_id},
        )
        db.execute(text("INSERT INTO public.attendance_records (booking_id, signed_in_at) VALUES (:b, now())"), {"b": other})
