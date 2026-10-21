"""
The staff kiosk (operations, docs/portals.md): nobody is logged in. The
paired tablet alone shows the staff list and the run sheet without personal
details; every other request carries a staff member and their PIN, is
checked against their role's kiosk permissions, and runs as them through
the normal services, recorded against them and the device.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from app.kiosk.dependencies import PIN_HEADER, STAFF_HEADER
from tests.factories import Api, StaffMember


BASE = "/staff-kiosk/v1/location1"


def _as(staff: StaffMember, pin: str | None = None) -> dict:
    """The headers one staff kiosk action carries."""
    return {STAFF_HEADER: staff.user_id, PIN_HEADER: pin or staff.pin}


@pytest.fixture
def staff_tablet(api: Api, admin):
    return api.kiosk(admin, "staff")


def _clock_in(tablet, staff: StaffMember, **body):
    return tablet.post(f"{BASE}/shift", json={"action": "start", **body}, headers=_as(staff))


@pytest.fixture
def staff(api: Api, staff_tablet) -> StaffMember:
    """A staff member, clocked in at the staff kiosk (only they can act)."""
    member = api.new_staff()
    assert _clock_in(staff_tablet, member).status_code == 200

    return member


@pytest.fixture
def family(api: Api, customer):
    """A customer with a child booked today."""
    child = api.new_child(customer)

    return child, api.booking_today(customer, child["id"])


def _sign(tablet, staff: StaffMember, **body):
    return tablet.post(f"{BASE}/sign", json=body, headers=_as(staff))


def _board_entry(tablet, booking_id: str) -> dict:
    [entry] = [e for e in tablet.get(f"{BASE}/board").json()["data"]["entries"] if e["booking_id"] == booking_id]

    return entry


def _roll_entry(tablet, staff: StaffMember, booking_id: str, date: str | None = None) -> dict:
    params = {"date": date} if date else {}
    data = tablet.get(f"{BASE}/roll", params=params, headers=_as(staff)).json()["data"]
    [entry] = [e for e in data["entries"] if e["booking_id"] == booking_id]

    return entry


def _holder(api: Api, customer) -> str:
    [(person_id,)] = api.sql(
        "SELECT id::text FROM public.authorized_pickup_persons WHERE lower(email) = lower(:email)",
        email=customer.email,
    )

    return person_id


# ---------------------------------------------------------------------------
# Before anyone enters a PIN
# ---------------------------------------------------------------------------

# The tablet shows the staff to choose from, and whether each has a PIN.
def test_staff_list(staff_tablet, staff):
    members = staff_tablet.get(f"{BASE}/staff").json()["data"]
    [me] = [m for m in members if m["user_id"] == staff.user_id]

    assert me["has_pin"] is True


# The run sheet shows names, sessions, status and a medical marker, but no
# family contacts, without a PIN.
def test_board_without_a_pin(api: Api, staff_tablet, customer):
    child = api.new_child(customer, allergy_info="Peanuts")
    api.sql("UPDATE public.child_medical_state SET review_status = 'approved' WHERE child_id = :id", id=child["id"])
    booking_id = api.booking_today(customer, child["id"])

    entry = _board_entry(staff_tablet, booking_id)

    assert entry["child_first_name"] == child["first_name"]
    assert entry["has_medical"] is True
    assert "family_phone" not in entry
    assert "family_first_name" not in entry


# Anything with personal details needs a PIN: the full roll included.
def test_details_need_a_pin(staff_tablet, family):
    assert staff_tablet.get(f"{BASE}/roll").status_code == 401
    assert staff_tablet.post(f"{BASE}/sign", json={"booking_id": family[1], "action": "in"}).status_code == 401


# A family kiosk can't be used as the staff kiosk.
def test_family_kiosk_cannot_use_staff_endpoints(api: Api, admin):
    family_tablet = api.kiosk(admin, "family")

    assert family_tablet.get(f"{BASE}/staff").status_code == 403


# ---------------------------------------------------------------------------
# PINs
# ---------------------------------------------------------------------------

# A task starts by checking the PIN.
def test_verify(staff_tablet, staff):
    response = staff_tablet.post(f"{BASE}/verify", headers=_as(staff))

    assert response.status_code == 200, response.text
    assert response.json()["data"]["user_id"] == staff.user_id


# Five wrong PINs lock it, even the right one then fails; a new PIN set on
# the website unlocks it.
def test_wrong_pins_lock_and_the_website_unlocks(staff_tablet, staff):
    for _ in range(5):
        response = staff_tablet.post(f"{BASE}/verify", headers=_as(staff, "0000"))

    assert "locked" in response.json()["msg"]
    assert staff_tablet.post(f"{BASE}/verify", headers=_as(staff)).status_code == 401

    staff.client.put("/staff-pin/v1/", json={"password": "Password123", "pin": staff.pin})
    assert staff_tablet.post(f"{BASE}/verify", headers=_as(staff)).status_code == 200


# Someone who isn't staff at this location can't act at the staff kiosk.
def test_non_staff_cannot_act(api: Api, staff_tablet, customer):
    [(customer_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :email", email=customer.email)

    response = staff_tablet.post(f"{BASE}/verify", headers={STAFF_HEADER: customer_id, PIN_HEADER: "1234"})

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Attendance, as the staff member
# ---------------------------------------------------------------------------

# Staff sign a child in (e.g. arriving from school), recorded against them
# and this tablet.
def test_staff_sign_in(api: Api, staff_tablet, staff, family):
    _, booking_id = family

    response = _sign(staff_tablet, staff, booking_id=booking_id, action="in")
    assert response.status_code == 200, response.text

    [(by_staff, device)] = api.sql(
        "SELECT signed_in_by_user_id::text, signed_in_kiosk_device_id IS NOT NULL "
        "FROM public.attendance_records WHERE booking_id = :id",
        id=booking_id,
    )
    assert (by_staff, device) == (staff.user_id, True)


# Signing out to someone not yet approved is refused; once staff check
# their ID (which approves them), it's allowed and records who collected.
def test_sign_out_after_checking_id(api: Api, staff_tablet, staff, customer, family):
    _, booking_id = family
    holder = _holder(api, customer)
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")

    refused = _sign(staff_tablet, staff, booking_id=booking_id, action="out", collected_by_pickup_person_id=holder)
    assert refused.status_code == 409

    response = staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(staff))
    assert response.status_code == 200, response.text
    assert response.json()["data"]["staff_approved_at"] is not None

    response = _sign(staff_tablet, staff, booking_id=booking_id, action="out", collected_by_pickup_person_id=holder)
    assert response.status_code == 200, response.text
    entry = _roll_entry(staff_tablet, staff, booking_id)
    assert entry["collected_by"]
    assert entry["collector_id_sighted"] is True


# Approving without ID approves without claiming ID was seen.
def test_approve_without_id(api: Api, staff_tablet, staff, customer, family):
    holder = _holder(api, customer)

    data = staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": False}, headers=_as(staff)).json()["data"]

    assert data["identity_verified_at"] is None
    assert data["staff_approved_at"] is not None


# Someone approved without ID can collect, and the roll records that their
# ID hadn't been sighted; checking it later doesn't rewrite that sign-out.
def test_collected_without_id_is_recorded(api: Api, staff_tablet, staff, customer, family):
    _, booking_id = family
    holder = _holder(api, customer)
    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": False}, headers=_as(staff))
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")

    response = _sign(staff_tablet, staff, booking_id=booking_id, action="out", collected_by_pickup_person_id=holder)
    assert response.status_code == 200, response.text
    assert _roll_entry(staff_tablet, staff, booking_id)["collector_id_sighted"] is False

    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(staff))
    assert _roll_entry(staff_tablet, staff, booking_id)["collector_id_sighted"] is False


# A one-off release names the person and how it was confirmed; a sign-out
# with no collector is refused.
def test_one_off_release(staff_tablet, staff, family):
    _, booking_id = family
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")

    assert _sign(staff_tablet, staff, booking_id=booking_id, action="out").status_code == 400
    assert _sign(staff_tablet, staff, booking_id=booking_id, action="out", released_to_name="Pat Lee").status_code == 422

    response = _sign(
        staff_tablet, staff,
        booking_id=booking_id, action="out",
        released_to_name="Pat Lee", release_note="Phoned the account holder 5:40pm; licence checked",
    )
    assert response.status_code == 200, response.text
    assert _roll_entry(staff_tablet, staff, booking_id)["released_to_name"] == "Pat Lee"


# A child who was never signed in can't be signed out.
def test_cannot_sign_out_a_child_never_signed_in(api: Api, staff_tablet, staff, customer, family):
    holder = _holder(api, customer)
    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(staff))

    response = _sign(staff_tablet, staff, booking_id=family[1], action="out", collected_by_pickup_person_id=holder)

    assert response.status_code == 409


# Staff can fix an earlier day, but never sign in a session yet to come.
def test_earlier_days_but_not_later_ones(api: Api, staff_tablet, staff, customer):
    child = api.new_child(customer)
    yesterday = api.booking_on(customer, child["id"], days_from_today=-1)

    response = _sign(staff_tablet, staff, booking_id=yesterday, action="in", at="2000-01-01T15:00:00+10:00")
    assert response.status_code == 200, response.text

    later_child = api.new_child(customer)
    data = api.book(customer, {later_child["id"]: [api.service_day()]}).json()["data"]
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))
    [(later,)] = api.sql("SELECT id::text FROM public.bookings WHERE booking_group_id = :g", g=data["booking_group_id"])

    assert _sign(staff_tablet, staff, booking_id=later, action="in").status_code == 409


# Undo clears a sign-out, then the sign-in.
def test_undo(api: Api, staff_tablet, staff, customer, family):
    _, booking_id = family
    holder = _holder(api, customer)
    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(staff))
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")
    _sign(staff_tablet, staff, booking_id=booking_id, action="out", collected_by_pickup_person_id=holder)

    staff_tablet.post(f"{BASE}/undo", json={"booking_id": booking_id, "step": "sign_out"}, headers=_as(staff))
    entry = _roll_entry(staff_tablet, staff, booking_id)
    assert (entry["signed_out_at"], entry["collected_by"]) == (None, None)
    assert entry["signed_in_at"] is not None

    staff_tablet.post(f"{BASE}/undo", json={"booking_id": booking_id, "step": "sign_in"}, headers=_as(staff))
    assert _roll_entry(staff_tablet, staff, booking_id)["signed_in_at"] is None


# Another location's bookings aren't reachable from this kiosk.
def test_other_locations_bookings_are_not_found(api: Api, staff_tablet, staff):
    other = api.new_customer(tenant="tenant2", location="location2")
    child = api.new_child(other)
    booking_id = api.booking_today(other, child["id"], tenant="tenant2", location="location2")

    assert _sign(staff_tablet, staff, booking_id=booking_id, action="in").status_code == 404


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------

# Starting a shift twice keeps the first start; ending records the end, and
# ending again changes nothing.
def test_shifts(api: Api, staff_tablet):
    staff = api.new_staff()

    first = staff_tablet.post(f"{BASE}/shift", json={"action": "start"}, headers=_as(staff)).json()["data"]
    second = staff_tablet.post(f"{BASE}/shift", json={"action": "start"}, headers=_as(staff)).json()["data"]
    assert first["started_at"] == second["started_at"]

    ended = staff_tablet.post(f"{BASE}/shift", json={"action": "end"}, headers=_as(staff)).json()["data"]
    assert ended["ended_at"] is not None

    again = staff_tablet.post(f"{BASE}/shift", json={"action": "end"}, headers=_as(staff)).json()["data"]
    assert again["ended_at"] is None


# The staff list on the tablet shows who's on shift, and since when.
def test_on_shift_shows_on_the_staff_list(staff_tablet, staff):
    [me] = [m for m in staff_tablet.get(f"{BASE}/staff").json()["data"] if m["user_id"] == staff.user_id]

    assert me["on_shift"] is True
    assert me["shift_started_at"] is not None
    assert me["unclosed_shift_started_at"] is None
    assert me["is_admin"] is False


# Someone who hasn't clocked in can't act at the staff kiosk, even with the
# right PIN; clocking in is the one thing they can do.
def test_must_be_on_shift_to_act(api: Api, staff_tablet, family):
    off_shift = api.new_staff()

    response = staff_tablet.post(f"{BASE}/verify", headers=_as(off_shift))
    assert response.status_code == 403
    assert "Clock in" in response.json()["msg"]
    assert _sign(staff_tablet, off_shift, booking_id=family[1], action="in").status_code == 403

    assert _clock_in(staff_tablet, off_shift).status_code == 200
    assert _sign(staff_tablet, off_shift, booking_id=family[1], action="in").status_code == 200


# A shift left open from yesterday doesn't count. Clocking in again asks
# when they left, closes that shift then, and starts a new one.
def test_forgotten_clock_out(api: Api, staff_tablet, staff):
    api.sql(
        "UPDATE public.staff_shifts SET started_at = started_at - interval '1 day' "
        "WHERE user_id = CAST(:id AS uuid) AND ended_at IS NULL",
        id=staff.user_id,
    )
    [(started_at,)] = api.sql(
        "SELECT started_at FROM public.staff_shifts WHERE user_id = CAST(:id AS uuid) AND ended_at IS NULL",
        id=staff.user_id,
    )

    [me] = [m for m in staff_tablet.get(f"{BASE}/staff").json()["data"] if m["user_id"] == staff.user_id]
    assert me["on_shift"] is False
    assert me["unclosed_shift_started_at"] is not None
    assert staff_tablet.post(f"{BASE}/verify", headers=_as(staff)).status_code == 403

    assert _clock_in(staff_tablet, staff).status_code == 409

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert _clock_in(staff_tablet, staff, previous_shift_ended_at=future).status_code == 400

    left = started_at + timedelta(hours=3)
    response = _clock_in(staff_tablet, staff, previous_shift_ended_at=left.isoformat())
    assert response.status_code == 200, response.text

    [(ended_at,)] = api.sql(
        "SELECT ended_at FROM public.staff_shifts WHERE user_id = CAST(:id AS uuid) AND started_at = :started",
        id=staff.user_id,
        started=started_at,
    )
    assert ended_at == left
    assert staff_tablet.post(f"{BASE}/verify", headers=_as(staff)).status_code == 200


# The database refuses attendance from staff at the kiosk who aren't on
# shift, whatever the API does.
def test_database_requires_a_shift(api: Api, staff_tablet, family):
    off_shift = api.new_staff()
    [(location_id, device_id)] = api.sql(
        "SELECT d.location_id::text, d.id::text FROM public.location_kiosk_devices d "
        "JOIN tenancy.locations l ON l.id = d.location_id JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1' AND d.kind = 'staff' AND d.is_active"
    )

    with SessionLocal() as db, pytest.raises(Exception, match="on shift"):
        db.execute(
            text(
                "SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true), "
                "set_config('app.channel', 'kiosk', true), set_config('app.kiosk_device_id', :d, true)"
            ),
            {"u": off_shift.user_id, "l": location_id, "d": device_id},
        )
        db.execute(
            text("INSERT INTO public.attendance_records (booking_id, signed_in_at) VALUES (:b, now())"),
            {"b": family[1]},
        )


# Before a PIN, the run sheet says who signed each child in and out, with
# shortened names only.
def test_board_shows_who_with_short_names(api: Api, staff_tablet, staff, customer, family):
    _, booking_id = family
    holder = _holder(api, customer)
    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": False}, headers=_as(staff))
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")
    _sign(staff_tablet, staff, booking_id=booking_id, action="out", collected_by_pickup_person_id=holder)

    entry = _board_entry(staff_tablet, booking_id)

    assert entry["signed_in_by"] == "Staff M."
    assert re.fullmatch(r"\S+ \S\.", entry["collected_by"])
    assert entry["collector_id_sighted"] is False
    assert entry["released_to"] is None


# A one-off release shows on the run sheet as the person's shortened name.
def test_board_shows_one_off_release_short(staff_tablet, staff, family):
    _, booking_id = family
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")
    _sign(
        staff_tablet, staff,
        booking_id=booking_id, action="out",
        released_to_name="Pat van Lee", release_note="Phoned the account holder",
    )

    entry = _board_entry(staff_tablet, booking_id)

    assert (entry["released_to"], entry["collected_by"]) == ("Pat v.", None)


# The run sheet lists the day's sessions with their places: the children on
# it are the confirmed bookings, and a booking awaiting payment holds a
# place without appearing on it. (Other tests move children into today's
# session past its capacity, so this one gives it room, then puts it back.)
def test_board_sessions_and_places(api: Api, staff_tablet, customer, family):
    _, booking_id = family

    def session_of_booking():
        board = staff_tablet.get(f"{BASE}/board").json()["data"]
        [entry] = [e for e in board["entries"] if e["booking_id"] == booking_id]

        def same(item):
            return (item["service_name"], item["start_time"]) == (entry["service_name"], entry["start_time"])

        [session] = [s for s in board["sessions"] if same(s)]

        return session, [e for e in board["entries"] if same(e)]

    day_id = session_of_booking()[0]["location_service_day_id"]
    [(capacity,)] = api.sql("SELECT capacity FROM public.location_service_days WHERE id = CAST(:id AS uuid)", id=day_id)
    api.sql(
        "UPDATE public.location_service_days d SET capacity = ("
        "  SELECT count(*) + 50 FROM public.bookings b WHERE b.location_service_day_id = d.id"
        ") WHERE d.id = CAST(:id AS uuid)",
        id=day_id,
    )

    try:
        _check_session_places(api, customer, session_of_booking)
    finally:
        api.sql("UPDATE public.location_service_days SET capacity = :c WHERE id = CAST(:id AS uuid)", c=capacity, id=day_id)


def _check_session_places(api: Api, customer, session_of_booking):
    before, shown = session_of_booking()
    assert before["booked"] == len(shown)
    assert before["places_left"] + before["booked"] + before["awaiting_payment"] == before["capacity"]

    child = api.new_child(customer)
    data = api.book(customer, {child["id"]: [api.service_day()]}).json()["data"]
    api.sql(
        "UPDATE public.bookings SET location_service_day_id = CAST(:day AS uuid) WHERE booking_group_id = CAST(:g AS uuid)",
        day=before["location_service_day_id"],
        g=data["booking_group_id"],
    )

    after, _ = session_of_booking()
    assert after["awaiting_payment"] == before["awaiting_payment"] + 1
    assert after["booked"] == before["booked"]
    assert after["places_left"] == before["places_left"] - 1


# ---------------------------------------------------------------------------
# Several children at once
# ---------------------------------------------------------------------------

def _bulk(tablet, staff: StaffMember, action: str, booking_ids: list[str]):
    return tablet.post(f"{BASE}/bulk", json={"action": action, "booking_ids": booking_ids}, headers=_as(staff))


# A session's arrivals are signed in together, each recorded against the
# staff member.
def test_bulk_sign_in(api: Api, staff_tablet, staff, customer):
    bookings = [api.booking_today(customer, api.new_child(customer)["id"]) for _ in range(2)]

    response = _bulk(staff_tablet, staff, "sign_in", bookings)
    assert response.status_code == 200, response.text

    for booking_id in bookings:
        entry = _roll_entry(staff_tablet, staff, booking_id)
        assert entry["signed_in_at"] is not None


# All or nothing: if one child can't be signed in, none are, and the error
# names that child.
def test_bulk_is_all_or_nothing(api: Api, staff_tablet, staff, customer):
    today = api.booking_today(customer, api.new_child(customer)["id"])
    later_child = api.new_child(customer, first_name="Mia")
    data = api.book(customer, {later_child["id"]: [api.service_day()]}).json()["data"]
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))
    [(later,)] = api.sql("SELECT id::text FROM public.bookings WHERE booking_group_id = :g", g=data["booking_group_id"])

    response = _bulk(staff_tablet, staff, "sign_in", [today, later])

    assert response.status_code == 409
    assert response.json()["msg"].startswith("Mia:")
    assert _roll_entry(staff_tablet, staff, today)["signed_in_at"] is None


# Before school children are sent to school together; the run sheet shows
# it, and undo clears it.
def test_send_to_school(api: Api, staff_tablet, staff, customer):
    bookings = [
        api.booking_today(customer, api.new_child(customer)["id"], service="before_school_care")
        for _ in range(2)
    ]
    _bulk(staff_tablet, staff, "sign_in", bookings)

    response = _bulk(staff_tablet, staff, "to_school", bookings)
    assert response.status_code == 200, response.text

    for booking_id in bookings:
        assert _roll_entry(staff_tablet, staff, booking_id)["sent_to_school"] is True
        assert _board_entry(staff_tablet, booking_id)["sent_to_school"] is True

    staff_tablet.post(f"{BASE}/undo", json={"booking_id": bookings[0], "step": "sign_out"}, headers=_as(staff))
    entry = _roll_entry(staff_tablet, staff, bookings[0])
    assert (entry["signed_out_at"], entry["sent_to_school"]) == (None, False)


# One before school child can be sent to school on their own too.
def test_send_one_to_school(api: Api, staff_tablet, staff, customer):
    booking_id = api.booking_today(customer, api.new_child(customer)["id"], service="before_school_care")
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")

    response = _sign(staff_tablet, staff, booking_id=booking_id, action="out", sent_to_school=True)

    assert response.status_code == 200, response.text
    assert _roll_entry(staff_tablet, staff, booking_id)["sent_to_school"] is True


# Only before school care children are sent to school.
def test_only_before_school_goes_to_school(api: Api, staff_tablet, staff, family):
    _, booking_id = family
    _sign(staff_tablet, staff, booking_id=booking_id, action="in")

    response = _bulk(staff_tablet, staff, "to_school", [booking_id])

    assert response.status_code == 409
    assert _roll_entry(staff_tablet, staff, booking_id)["signed_out_at"] is None


# ---------------------------------------------------------------------------
# Service times apply to staff too
# ---------------------------------------------------------------------------

# With service times on, staff can't sign children in more than 2 hours
# before the session either, one at a time or together; the run sheet says
# when signing opens.
def test_staff_signing_follows_service_times(staff_tablet, staff, family, service_times):
    _, booking_id = family
    service_times(3)

    assert _sign(staff_tablet, staff, booking_id=booking_id, action="in").status_code == 409
    assert _bulk(staff_tablet, staff, "sign_in", [booking_id]).status_code == 409
    assert all(s["signing_opens_at"] for s in staff_tablet.get(f"{BASE}/board").json()["data"]["sessions"]
               if s["service_code"] == "after_school_care")

    service_times(1)
    assert _sign(staff_tablet, staff, booking_id=booking_id, action="in").status_code == 200


# Correcting an earlier day goes by when it happened: a time inside that
# day's window is accepted.
def test_staff_correct_an_earlier_day_within_its_times(api: Api, staff_tablet, staff, customer, service_times):
    yesterday = api.booking_on(customer, api.new_child(customer)["id"], days_from_today=-1)
    service_times(1)
    at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    response = _sign(staff_tablet, staff, booking_id=yesterday, action="in", at=at)

    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Medical details and action plans
# ---------------------------------------------------------------------------

def _set_review(api: Api, child_id: str, status: str):
    api.sql(
        "UPDATE public.child_medical_state SET review_status = CAST(:s AS public.medical_review_status_enum) "
        "WHERE child_id = CAST(:id AS uuid)",
        s=status,
        id=child_id,
    )


# With a PIN, staff see a child's medical details, review status and
# documents, and can open a document.
def test_child_medical_details(api: Api, staff_tablet, staff, customer):
    child = api.new_child(customer, allergy_info="Peanuts: anaphylaxis")
    document = api.upload_document(customer, child["id"])
    _set_review(api, child["id"], "approved")

    response = staff_tablet.get(f"{BASE}/children/{child['id']}/medical", headers=_as(staff))
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert data["allergy_info"] == "Peanuts: anaphylaxis"
    assert data["review_status"] == "approved"
    assert [d["id"] for d in data["documents"]] == [document["id"]]

    response = staff_tablet.get(f"{BASE}/documents/{document['id']}/download", headers=_as(staff))
    assert response.status_code == 200, response.text
    assert response.json()["data"]["url"]


# Medical details need a PIN, and another business's children aren't found.
def test_medical_details_need_a_pin_and_stay_at_the_location(api: Api, staff_tablet, staff, customer):
    child = api.new_child(customer, allergy_info="Peanuts")
    other = api.new_customer(tenant="tenant2", location="location2")
    other_child = api.new_child(other, allergy_info="Bees")

    assert staff_tablet.get(f"{BASE}/children/{child['id']}/medical").status_code == 401
    assert staff_tablet.get(f"{BASE}/children/{other_child['id']}/medical", headers=_as(staff)).status_code == 404


# The action plan list has the location's children with plans, by name. A
# plan is new while it's not yet reviewed, or for 7 days after upload.
def test_action_plans(api: Api, staff_tablet, staff, customer):
    reviewed_old = api.new_child(customer, first_name="Aaron", allergy_info="Peanuts")
    reviewed_recent = api.new_child(customer, first_name="Bella", allergy_info="Peanuts")
    unreviewed_old = api.new_child(customer, first_name="Cody", allergy_info="Peanuts")
    no_plan = api.new_child(customer, first_name="Dana")

    plans = {}
    for child in (reviewed_old, reviewed_recent, unreviewed_old):
        plans[child["id"]] = api.upload_document(customer, child["id"])["id"]
    api.upload_document(customer, no_plan["id"], document_type="other")

    _set_review(api, reviewed_old["id"], "approved")
    _set_review(api, reviewed_recent["id"], "approved")
    api.sql(
        "UPDATE public.child_documents SET created_at = now() - interval '30 days' WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))",
        a=plans[reviewed_old["id"]],
        b=plans[unreviewed_old["id"]],
    )

    response = staff_tablet.get(f"{BASE}/action-plans", headers=_as(staff))
    assert response.status_code == 200, response.text

    mine = [p for p in response.json()["data"] if p["child_id"] in {c["id"] for c in (reviewed_old, reviewed_recent, unreviewed_old, no_plan)}]
    assert [(p["child_first_name"], p["is_new"]) for p in mine] == [("Aaron", False), ("Bella", True), ("Cody", True)]


# ---------------------------------------------------------------------------
# Brothers and sisters signed out together
# ---------------------------------------------------------------------------

# Brothers and sisters are signed out to the same approved person in one go.
def test_siblings_signed_out_together(api: Api, staff_tablet, staff, customer):
    holder = _holder(api, customer)
    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(staff))
    bookings = [api.booking_today(customer, api.new_child(customer)["id"]) for _ in range(2)]
    _bulk(staff_tablet, staff, "sign_in", bookings)

    response = staff_tablet.post(
        f"{BASE}/bulk",
        json={"action": "sign_out", "booking_ids": bookings, "collected_by_pickup_person_id": holder},
        headers=_as(staff),
    )
    assert response.status_code == 200, response.text

    for booking_id in bookings:
        assert _roll_entry(staff_tablet, staff, booking_id)["collected_by"]


# All or nothing: if one of them was never signed in, neither is signed out.
def test_siblings_all_or_nothing(api: Api, staff_tablet, staff, customer):
    holder = _holder(api, customer)
    staff_tablet.post(f"{BASE}/check-id", json={"pickup_person_id": holder, "id_seen": True}, headers=_as(staff))
    here = api.booking_today(customer, api.new_child(customer)["id"])
    not_here = api.booking_today(customer, api.new_child(customer, first_name="Mia")["id"])
    _sign(staff_tablet, staff, booking_id=here, action="in")

    response = staff_tablet.post(
        f"{BASE}/bulk",
        json={"action": "sign_out", "booking_ids": [here, not_here], "collected_by_pickup_person_id": holder},
        headers=_as(staff),
    )

    assert response.status_code == 409
    assert response.json()["msg"].startswith("Mia:")
    assert _roll_entry(staff_tablet, staff, here)["signed_out_at"] is None


# A one-off release of several children needs how it was confirmed.
def test_siblings_one_off_release_needs_a_note(staff_tablet, staff, family):
    response = staff_tablet.post(
        f"{BASE}/bulk",
        json={"action": "sign_out", "booking_ids": [family[1]], "released_to_name": "Pat Lee"},
        headers=_as(staff),
    )

    assert response.status_code == 422


# Staff tick that they've printed a plan for the folder; the list says who
# and when, and unticking corrects a mistake.
def test_mark_plan_printed(api: Api, staff_tablet, staff, customer):
    child = api.new_child(customer, allergy_info="Peanuts")
    document = api.upload_document(customer, child["id"])

    def plan():
        [mine] = [p for p in staff_tablet.get(f"{BASE}/action-plans", headers=_as(staff)).json()["data"]
                  if p["document_id"] == document["id"]]
        return mine

    assert (plan()["printed_at"], plan()["printed_by"]) == (None, None)

    response = staff_tablet.put(f"{BASE}/documents/{document['id']}/printed", json={"printed": True}, headers=_as(staff))
    assert response.status_code == 200, response.text
    assert plan()["printed_at"] is not None
    assert plan()["printed_by"] == "Staff M."

    staff_tablet.put(f"{BASE}/documents/{document['id']}/printed", json={"printed": False}, headers=_as(staff))
    assert (plan()["printed_at"], plan()["printed_by"]) == (None, None)


# Only staff on shift can tick it, and a family can't set it on their own
# documents.
def test_only_staff_on_shift_mark_printed(api: Api, staff_tablet, customer):
    child = api.new_child(customer, allergy_info="Peanuts")
    document = api.upload_document(customer, child["id"])
    off_shift = api.new_staff()

    response = staff_tablet.put(f"{BASE}/documents/{document['id']}/printed", json={"printed": True}, headers=_as(off_shift))
    assert response.status_code == 403

    [(customer_id, location_id)] = api.sql(
        "SELECT u.id::text, cp.location_id::text FROM auth.users u JOIN public.child_profile cp ON cp.user_id = u.id "
        "WHERE cp.id = CAST(:id AS uuid)",
        id=child["id"],
    )
    with SessionLocal() as db, pytest.raises(Exception, match="changed that way"):
        db.execute(
            text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
            {"u": customer_id, "l": location_id},
        )
        db.execute(
            text("UPDATE public.child_documents SET printed_at = now(), printed_by_user_id = CAST(:u AS uuid) WHERE id = CAST(:d AS uuid)"),
            {"u": customer_id, "d": document["id"]},
        )


# ---------------------------------------------------------------------------
# Bookings and refunds
# ---------------------------------------------------------------------------

# Staff see a family's bookings from today to 2 weeks ahead, and anything
# still awaiting payment whatever its date; later paid ones aren't listed.
def test_family_bookings(api: Api, staff_tablet, staff, customer, family):
    _, today = family
    later = api.new_child(customer)
    paid = api.book(customer, {later["id"]: [api.service_day()]}).json()["data"]
    api.webhook("checkout.session.completed", api.session_id(paid["checkout_url"]))
    [(paid_later,)] = api.sql("SELECT id::text FROM public.bookings WHERE booking_group_id = :g", g=paid["booking_group_id"])
    unpaid = api.book(customer, {later["id"]: [api.service_day()]}).json()["data"]
    [(unpaid_later,)] = api.sql("SELECT id::text FROM public.bookings WHERE booking_group_id = :g", g=unpaid["booking_group_id"])
    [(family_user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    response = staff_tablet.get(f"{BASE}/families/{family_user_id}/bookings", headers=_as(staff))
    assert response.status_code == 200, response.text

    listed = {b["id"]: b for b in response.json()["data"]}
    assert listed[today]["payment_status"] == "PAID"
    assert listed[unpaid_later]["booking_status"] == "PENDING"
    assert paid_later not in listed


# Staff find a family by a child's first or last name, at this location only.
def test_child_search(api: Api, staff_tablet, staff, customer):
    child = api.new_child(customer, first_name="Zebedee")
    other = api.new_customer(tenant="tenant2", location="location2")
    api.new_child(other, first_name="Zebulon")

    response = staff_tablet.get(f"{BASE}/children/search", params={"q": "zeb"}, headers=_as(staff))
    assert response.status_code == 200, response.text

    found = response.json()["data"]
    assert child["id"] in [c["child_id"] for c in found]
    assert all(c["first_name"] != "Zebulon" for c in found)
    assert staff_tablet.get(f"{BASE}/children/search", params={"q": "z"}, headers=_as(staff)).status_code == 422


# An admin on shift refunds one booking at the kiosk, even on its own day
# (past the family's cutoff); staff can't.
def test_admin_refunds_at_the_kiosk(api: Api, staff_tablet, staff, family):
    _, booking_id = family
    admin_member = api.new_staff(role="admin")
    assert _clock_in(staff_tablet, admin_member).status_code == 200

    refused = staff_tablet.post(f"{BASE}/refunds", json={"booking_id": booking_id}, headers=_as(staff))
    assert refused.status_code == 403

    response = staff_tablet.post(f"{BASE}/refunds", json={"booking_id": booking_id}, headers=_as(admin_member))
    assert response.status_code == 201, response.text

    [(requested_by, status)] = api.sql(
        "SELECT requested_by_user_id::text, status::text FROM public.refunds WHERE booking_id = CAST(:b AS uuid)",
        b=booking_id,
    )
    assert requested_by == admin_member.user_id
    assert status in ("PENDING", "SUCCEEDED")
