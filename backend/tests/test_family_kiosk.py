"""
The family kiosk (app/kiosk, schema/0004 kiosk_*): a paired tablet where
pickup people log in with their mobile and PIN and sign their family's
children in and out for today's sessions. The device cookie says which
tablet it is; a 60-second session token says who is using it.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.integrations.email.messages import KioskPinEmail
from app.kiosk import tokens
from tests.factories import Api


BASE = "/kiosk/v1/location1"


def _pin_for(sent_emails, email: str) -> str:
    """The latest kiosk PIN emailed to this address."""
    return [m.pin for m in sent_emails(KioskPinEmail) if m.to_email == email][-1]


def _login(tablet, phone: str, pin: str):
    return tablet.post(f"{BASE}/login", json={"phone": phone, "pin": pin})


def _headers(token: str) -> dict:
    return {tokens.SESSION_HEADER: token}


def _ready(tablet, customer, sent_emails) -> str:
    """Log the account holder in and choose their own PIN; returns a session token."""
    response = _login(tablet, customer.phone, _pin_for(sent_emails, customer.email))
    assert response.status_code == 200, response.text

    response = tablet.post(
        f"{BASE}/pin",
        json={"new_pin": "2468"},
        headers=_headers(response.json()["data"]["session"]["token"]),
    )
    assert response.status_code == 200, response.text

    return response.json()["data"]["token"]


def _approve(api: Api, email: str):
    """Staff approve the person (the staff kiosk isn't built in these tests)."""
    api.sql(
        "UPDATE public.authorized_pickup_persons SET staff_approved_at = now() WHERE lower(email) = lower(:email)",
        email=email,
    )


@pytest.fixture
def tablet(api: Api, admin):
    return api.kiosk(admin, "family")


@pytest.fixture
def family(api: Api, customer, sent_emails):
    """A customer with a child booked for today (their first child gets them a PIN)."""
    child = api.new_child(customer)
    booking_id = api.booking_today(customer, child["id"])

    return child, booking_id


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------

# A paired tablet knows it's this centre's family kiosk.
def test_paired_tablet_describes_itself(tablet):
    response = tablet.get(f"{BASE}/device")

    assert response.status_code == 200, response.text
    assert response.json()["data"]["kind"] == "family"


# The tablet also gets the centre's sessions today for its welcome screen:
# the timetable only, nothing about families or children (it's shown before
# anyone logs in). With service times not enforced (the tests' default),
# signing is open all day, so there are no opening and closing times.
def test_tablet_shows_todays_sessions(tablet, family):
    sessions = tablet.get(f"{BASE}/device").json()["data"]["sessions_today"]

    assert sessions, "today's session should be listed"
    assert all(
        set(session) == {"service_name", "start_time", "end_time", "signing_opens_at", "signing_closes_at"}
        for session in sessions
    )
    assert all(session["signing_opens_at"] is None and session["signing_closes_at"] is None for session in sessions)


# When the centre enforces service times, each of today's sessions on the
# welcome screen says when signing opens and closes: 2 hours either side.
def test_todays_sessions_show_signing_times(api: Api, tablet, family, service_times):
    service_times(1)
    [(after_school,)] = api.sql("SELECT name FROM public.service_types WHERE code = 'after_school_care'")

    sessions = tablet.get(f"{BASE}/device").json()["data"]["sessions_today"]
    [session] = [s for s in sessions if s["service_name"] == after_school]

    opens = datetime.fromisoformat(session["signing_opens_at"])
    closes = datetime.fromisoformat(session["signing_closes_at"])

    # The (moved) one-hour session, open from 2 hours before to 2 hours after.
    assert closes - opens == timedelta(hours=5)


# A browser that was never paired is told to set the kiosk up.
def test_unpaired_browser_is_refused(api: Api):
    assert api.client().get(f"{BASE}/device").status_code == 401


# A setup code works once, and not after it expires.
def test_setup_code_is_single_use_and_expires(api: Api, admin):
    api.sql("UPDATE public.location_kiosk_devices SET is_active = FALSE WHERE kind = 'family'")
    code = admin.post("/kiosk-devices/v1/", json={"kind": "family", "name": "Front"}).json()["data"]["setup_code"]

    assert api.client().post(f"{BASE}/pair", json={"code": code.lower()}).status_code == 200
    assert api.client().post(f"{BASE}/pair", json={"code": code}).status_code == 400

    api.sql("UPDATE public.location_kiosk_devices SET is_active = FALSE WHERE kind = 'family'")
    code = admin.post("/kiosk-devices/v1/", json={"kind": "family", "name": "Front"}).json()["data"]["setup_code"]
    api.sql("UPDATE public.location_kiosk_devices SET setup_code_expires_at = now() - interval '1 minute' WHERE is_active AND kind = 'family'")

    assert api.client().post(f"{BASE}/pair", json={"code": code}).status_code == 400


# Revoking the kiosk stops the tablet working straight away.
def test_revoked_kiosk_stops_working(api: Api, admin, tablet):
    [device] = [d for d in admin.get("/kiosk-devices/v1/").json()["data"] if d["is_active"] and d["kind"] == "family"]

    admin.post(f"/kiosk-devices/v1/{device['id']}/revoke")

    assert tablet.get(f"{BASE}/device").status_code == 401


# A staff kiosk can't be used as the family kiosk.
def test_staff_kiosk_cannot_use_family_endpoints(api: Api, admin):
    staff_tablet = api.kiosk(admin, "staff")

    assert staff_tablet.get(f"{BASE}/device").status_code == 403


# ---------------------------------------------------------------------------
# Logging in and PINs
# ---------------------------------------------------------------------------

# A wrong PIN and an unknown number get the same answer.
def test_wrong_details_get_one_answer(tablet, customer, family):
    wrong_pin = _login(tablet, customer.phone, "0000")
    unknown = _login(tablet, "0499999999", "0000")

    assert wrong_pin.status_code == unknown.status_code == 401
    assert wrong_pin.json()["msg"] == unknown.json()["msg"]


# Five wrong PINs lock the person; even the right PIN won't work until a
# reset.
def test_five_wrong_pins_lock(tablet, customer, family, sent_emails):
    pin = _pin_for(sent_emails, customer.email)
    wrong = "0000" if pin != "0000" else "1111"

    for _ in range(5):
        response = _login(tablet, customer.phone, wrong)

    assert "Forgot PIN" in response.json()["msg"]
    assert _login(tablet, customer.phone, pin).status_code == 401


# The emailed PIN only gets you as far as choosing your own.
def test_setup_pin_must_be_changed_first(tablet, customer, family, sent_emails):
    response = _login(tablet, customer.phone, _pin_for(sent_emails, customer.email))
    data = response.json()["data"]
    assert data["pin_change_required"] is True

    assert tablet.get(f"{BASE}/today", headers=_headers(data["session"]["token"])).status_code == 403

    response = tablet.post(f"{BASE}/pin", json={"new_pin": "2468"}, headers=_headers(data["session"]["token"]))
    assert response.status_code == 200, response.text

    assert tablet.get(f"{BASE}/today", headers=_headers(response.json()["data"]["token"])).status_code == 200
    assert _login(tablet, customer.phone, "2468").json()["data"]["pin_change_required"] is False


# The new PIN has to be 4 digits and different from the emailed one.
def test_new_pin_rules(tablet, customer, family, sent_emails):
    pin = _pin_for(sent_emails, customer.email)
    token = _login(tablet, customer.phone, pin).json()["data"]["session"]["token"]

    assert tablet.post(f"{BASE}/pin", json={"new_pin": pin}, headers=_headers(token)).status_code == 400
    assert tablet.post(f"{BASE}/pin", json={"new_pin": "12a4"}, headers=_headers(token)).status_code == 400


# An emailed PIN that isn't used within 30 days stops working.
def test_unused_setup_pin_expires(api: Api, tablet, customer, family, sent_emails):
    api.sql(
        "UPDATE public.authorized_pickup_persons SET pin_issued_at = now() - interval '31 days' WHERE lower(email) = lower(:email)",
        email=customer.email,
    )

    response = _login(tablet, customer.phone, _pin_for(sent_emails, customer.email))

    assert response.status_code == 401
    assert "expired" in response.json()["msg"]


# Forgot PIN emails a new one (which also unlocks), at most every 20
# minutes, and answers the same for numbers that aren't registered.
def test_forgot_pin(tablet, customer, family, sent_emails):
    before = len(sent_emails(KioskPinEmail))

    for _ in range(5):
        _login(tablet, customer.phone, "0000")

    known = tablet.post(f"{BASE}/forgot-pin", json={"phone": customer.phone})
    again = tablet.post(f"{BASE}/forgot-pin", json={"phone": customer.phone})
    unknown = tablet.post(f"{BASE}/forgot-pin", json={"phone": "0499999999"})

    assert known.json()["msg"] == again.json()["msg"] == unknown.json()["msg"]
    assert len(sent_emails(KioskPinEmail)) == before + 1

    response = _login(tablet, customer.phone, _pin_for(sent_emails, customer.email))
    assert response.status_code == 200
    assert response.json()["data"]["pin_change_required"] is True


# ---------------------------------------------------------------------------
# Today's sessions
# ---------------------------------------------------------------------------

# A person sees their family's sessions for today, with the child's first
# name and initial only.
def test_today_shows_the_familys_sessions(tablet, customer, family, sent_emails):
    child, booking_id = family
    token = _ready(tablet, customer, sent_emails)

    response = tablet.get(f"{BASE}/today", headers=_headers(token))
    assert response.status_code == 200, response.text

    [booking] = response.json()["data"]["bookings"]
    assert booking["booking_id"] == booking_id
    assert booking["child_first_name"] == child["first_name"]
    assert booking["child_last_initial"] == child["last_name"][0]
    assert response.json()["data"]["session"]["token"]


# Another family's children, and future sessions, aren't shown.
def test_today_shows_nothing_else(api: Api, tablet, customer, other_customer, family, sent_emails):
    their_child = api.new_child(other_customer)
    api.booking_today(other_customer, their_child["id"])
    future_child = api.new_child(customer)
    api.book(customer, {future_child["id"]: [api.service_day()]})

    token = _ready(tablet, customer, sent_emails)
    bookings = tablet.get(f"{BASE}/today", headers=_headers(token)).json()["data"]["bookings"]

    assert [b["booking_id"] for b in bookings] == [family[1]]


# ---------------------------------------------------------------------------
# Signing in and out
# ---------------------------------------------------------------------------

def _sign(tablet, token: str, booking_id: str, action: str):
    return tablet.post(f"{BASE}/sign", json={"booking_id": booking_id, "action": action}, headers=_headers(token))


# Signing in records the time, the person and the kiosk; doing it again
# changes nothing.
def test_sign_in(api: Api, tablet, customer, family, sent_emails):
    _, booking_id = family
    token = _ready(tablet, customer, sent_emails)

    first = _sign(tablet, token, booking_id, "in")
    assert first.status_code == 200, first.text
    second = _sign(tablet, first.json()["data"]["session"]["token"], booking_id, "in")

    assert first.json()["data"]["signed_in_at"] == second.json()["data"]["signed_in_at"]

    [(by_person, device)] = api.sql(
        "SELECT signed_in_by_pickup_person_id IS NOT NULL, signed_in_kiosk_device_id IS NOT NULL "
        "FROM public.attendance_records WHERE booking_id = :id",
        id=booking_id,
    )
    assert by_person and device


# Collecting a child needs staff to have approved the person first.
def test_sign_out_needs_approval(api: Api, tablet, customer, family, sent_emails):
    _, booking_id = family
    token = _ready(tablet, customer, sent_emails)
    token = _sign(tablet, token, booking_id, "in").json()["data"]["session"]["token"]

    refused = _sign(tablet, token, booking_id, "out")
    assert refused.status_code == 409
    assert "staff member" in refused.json()["msg"]

    _approve(api, customer.email)

    response = _sign(tablet, token, booking_id, "out")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["signed_out_at"] is not None


# A child who was never signed in can't be signed out at the kiosk: staff
# should check, as the child may not be here.
def test_cannot_sign_out_a_child_never_signed_in(api: Api, tablet, customer, family, sent_emails):
    _, booking_id = family
    _approve(api, customer.email)
    token = _ready(tablet, customer, sent_emails)

    response = _sign(tablet, token, booking_id, "out")

    assert response.status_code == 409
    assert "hasn't been signed in" in response.json()["msg"]


# Another family's booking can't be signed in from someone else's session.
def test_cannot_sign_another_familys_child(api: Api, tablet, customer, other_customer, family, sent_emails):
    their_child = api.new_child(other_customer)
    their_booking = api.booking_today(other_customer, their_child["id"])
    token = _ready(tablet, customer, sent_emails)

    assert _sign(tablet, token, their_booking, "in").status_code == 404


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

# A session ends after 60 seconds idle: a token past its time is refused.
def test_expired_session_is_refused(tablet, customer, family, sent_emails, monkeypatch):
    token = _ready(tablet, customer, sent_emails)

    # The next token handed back is already past its 60 seconds.
    monkeypatch.setattr(tokens, "SESSION_IDLE", timedelta(seconds=-60))
    stale = tablet.get(f"{BASE}/today", headers=_headers(token)).json()["data"]["session"]["token"]

    assert tablet.get(f"{BASE}/today", headers=_headers(stale)).status_code == 401


# A session made on another tablet isn't accepted here.
def test_session_from_another_device_is_refused(tablet, customer, family):
    token, _ = tokens.issue_session_token(
        kind="family", device_id=uuid4(), location_id=uuid4(), subject_id=uuid4(),
    )

    assert tablet.get(f"{BASE}/today", headers=_headers(token)).status_code == 401


# No session, no access to anyone's children.
def test_today_needs_a_session(tablet):
    assert tablet.get(f"{BASE}/today").status_code == 401


# ---------------------------------------------------------------------------
# Service times: families sign in and out only around each session
# ---------------------------------------------------------------------------

# More than 2 hours before the session, the kiosk refuses to sign in.
def test_sign_in_too_early_is_refused(tablet, customer, family, sent_emails, service_times):
    _, booking_id = family
    service_times(3)
    token = _ready(tablet, customer, sent_emails)

    response = _sign(tablet, token, booking_id, "in")

    assert response.status_code == 409
    assert "2 hours" in response.json()["msg"]


# Within 2 hours of the session, signing in works.
def test_sign_in_around_the_session(tablet, customer, family, sent_emails, service_times):
    _, booking_id = family
    service_times(1)
    token = _ready(tablet, customer, sent_emails)

    response = _sign(tablet, token, booking_id, "in")

    assert response.status_code == 200, response.text


# More than 2 hours after the session, the kiosk refuses to sign out.
def test_sign_out_too_late_is_refused(api: Api, tablet, customer, family, sent_emails, service_times):
    _, booking_id = family
    _approve(api, customer.email)
    service_times(-1)
    token = _ready(tablet, customer, sent_emails)
    token = _sign(tablet, token, booking_id, "in").json()["data"]["session"]["token"]

    service_times(-4)
    response = _sign(tablet, token, booking_id, "out")

    assert response.status_code == 409
    assert "2 hours" in response.json()["msg"]


# The kiosk's list says when signing opens and closes, so it can show it
# instead of a button; with the setting off, there are no limits.
def test_today_shows_the_signing_times(api: Api, tablet, customer, family, sent_emails, service_times):
    service_times(3)
    token = _ready(tablet, customer, sent_emails)

    [booking] = tablet.get(f"{BASE}/today", headers=_headers(token)).json()["data"]["bookings"]
    assert booking["signing_opens_at"] is not None
    assert booking["signing_closes_at"] is not None

    api.sql(
        "UPDATE tenancy.locations l SET kiosk_enforce_service_times = FALSE "
        "FROM tenancy.tenants t WHERE t.id = l.tenant_id AND t.code = 'tenant1' AND l.code = 'location1'"
    )
    [booking] = tablet.get(f"{BASE}/today", headers=_headers(token)).json()["data"]["bookings"]
    assert (booking["signing_opens_at"], booking["signing_closes_at"]) == (None, None)


# Admins switch the rule on and off on the kiosks page; families can't.
def test_admin_switches_service_times(api: Api, admin, customer):
    try:
        response = admin.put("/kiosk-devices/v1/settings", json={"enforce_service_times": True})
        assert response.status_code == 200, response.text
        assert admin.get("/kiosk-devices/v1/settings").json()["data"]["enforce_service_times"] is True

        assert customer.client.put("/kiosk-devices/v1/settings", json={"enforce_service_times": False}).status_code == 403
    finally:
        api.sql(
        "UPDATE tenancy.locations l SET kiosk_enforce_service_times = FALSE "
        "FROM tenancy.tenants t WHERE t.id = l.tenant_id AND t.code = 'tenant1' AND l.code = 'location1'"
    )
