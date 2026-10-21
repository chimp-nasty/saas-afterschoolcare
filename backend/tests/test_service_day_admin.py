"""
Service days (Admin › Service days, slice 4-2): admins see each day's
places; superadmins add days, change places, close, reopen and delete them
(by permission). The database keeps bookings safe whoever does it: no days
in the past, places never below what's booked, no closing a booked day, no
deleting a day that's ever been booked.
"""

import itertools
from datetime import date, timedelta

import pytest

from tests.factories import Api


BASE = "/location-service-days/v1"

# Each test gets its own stretch of dates, far past any other test's days.
_blocks = itertools.count()


@pytest.fixture
def dates() -> date:
    """The first day of a fresh 3-week stretch, about 3 years out, on a Monday."""
    start = date.today() + timedelta(days=1100 + 21 * next(_blocks))

    return start + timedelta(days=(7 - start.weekday()) % 7)


def _after_school(client) -> str:
    services = client.get("/location-services/v1/settings").json()["data"]

    return next(s["id"] for s in services if s["service_name"] == "After School Care")


def _add(client, service_id: str, start: date, end: date, capacity: int = 20, **body):
    return client.post(
        f"{BASE}/",
        json={
            "location_service_id": service_id,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "capacity": capacity,
            **body,
        },
    )


def _overview(client, service_id: str, start: date, end: date) -> list[dict]:
    response = client.get(
        f"{BASE}/overview",
        params={"location_service_id": service_id, "date_from": start.isoformat(), "date_to": end.isoformat()},
    )
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _day(client, service_id: str, on: date) -> dict:
    [day] = _overview(client, service_id, on, on)

    return day


def _book(api: Api, customer, day_id: str, *, paid: bool = True):
    child = api.new_child(customer)
    data = api.book(customer, {child["id"]: [day_id]}).json()["data"]

    if paid:
        api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))


# A superadmin adds a fortnight of weekdays; adding the same range again
# skips them all.
def test_add_weekdays(superadmin, dates):
    service_id = _after_school(superadmin)
    end = dates + timedelta(days=13)

    response = _add(superadmin, service_id, dates, end, weekdays=[0, 1, 2, 3, 4])
    assert response.status_code == 201, response.text
    assert len(response.json()["data"]["created"]) == 10

    again = _add(superadmin, service_id, dates, end, weekdays=[0, 1, 2, 3, 4]).json()["data"]
    assert (again["created"], len(again["skipped"])) == ([], 10)

    assert all(d["capacity"] == 20 and d["is_open"] for d in _overview(superadmin, service_id, dates, end))


# One day is a range of one date.
def test_add_one_day(superadmin, dates):
    service_id = _after_school(superadmin)
    saturday = dates + timedelta(days=5)

    response = _add(superadmin, service_id, saturday, saturday, capacity=12)

    assert response.json()["data"]["created"] == [saturday.isoformat()]
    assert _day(superadmin, service_id, saturday)["capacity"] == 12


# Days can't be added in the past.
def test_no_days_in_the_past(superadmin):
    service_id = _after_school(superadmin)
    yesterday = date.today() - timedelta(days=1)

    response = _add(superadmin, service_id, yesterday, yesterday)

    assert response.status_code == 400
    assert "past" in response.json()["msg"]


# The overview shows each day's confirmed bookings, places held awaiting
# payment, and places left.
def test_overview_counts(api: Api, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    _add(superadmin, service_id, dates, dates, capacity=10)
    day = _day(superadmin, service_id, dates)

    _book(api, customer, day["id"])
    _book(api, customer, day["id"], paid=False)

    day = _day(superadmin, service_id, dates)
    assert (day["booked"], day["awaiting_payment"], day["places_left"]) == (1, 1, 8)
    assert day["ever_booked"] is True


# Places can't go below what's booked (counting bookings awaiting payment);
# above that they can.
def test_places_not_below_booked(api: Api, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    _add(superadmin, service_id, dates, dates, capacity=10)
    day = _day(superadmin, service_id, dates)
    _book(api, customer, day["id"])
    _book(api, customer, day["id"], paid=False)

    refused = superadmin.patch(f"{BASE}/{day['id']}", json={"capacity": 1})
    assert refused.status_code == 409
    assert "2 places are booked" in refused.json()["msg"]

    assert superadmin.patch(f"{BASE}/{day['id']}", json={"capacity": 2}).status_code == 200


# Places across a range are all or nothing: one booked day past the new
# places stops the lot, and is named.
def test_places_for_a_range(api: Api, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    end = dates + timedelta(days=1)
    _add(superadmin, service_id, dates, end, capacity=10)
    _book(api, customer, _day(superadmin, service_id, dates)["id"])

    body = {"location_service_id": service_id, "date_from": dates.isoformat(), "date_to": end.isoformat()}
    refused = superadmin.patch(f"{BASE}/capacity", json={**body, "capacity": 0})
    assert refused.status_code == 409
    assert dates.strftime("%a %d %b") in refused.json()["msg"]
    assert [d["capacity"] for d in _overview(superadmin, service_id, dates, end)] == [10, 10]

    response = superadmin.patch(f"{BASE}/capacity", json={**body, "capacity": 4})
    assert response.json()["data"]["updated"] == 2
    assert [d["capacity"] for d in _overview(superadmin, service_id, dates, end)] == [4, 4]


# An empty day can be closed with a reason, which stops bookings; reopening
# clears the reason.
def test_close_and_reopen(api: Api, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    _add(superadmin, service_id, dates, dates)
    day = _day(superadmin, service_id, dates)

    closed = superadmin.patch(f"{BASE}/{day['id']}", json={"is_open": False, "closed_reason": "  Staff training  "})
    assert closed.status_code == 200, closed.text
    assert (closed.json()["data"]["is_open"], closed.json()["data"]["closed_reason"]) == (False, "Staff training")

    child = api.new_child(customer)
    assert api.book(customer, {child["id"]: [day["id"]]}).status_code == 400

    reopened = superadmin.patch(f"{BASE}/{day['id']}", json={"is_open": True}).json()["data"]
    assert (reopened["is_open"], reopened["closed_reason"]) == (True, None)


# A day with bookings can't be closed: they're refunded first.
def test_cannot_close_a_booked_day(api: Api, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    _add(superadmin, service_id, dates, dates)
    day = _day(superadmin, service_id, dates)
    _book(api, customer, day["id"])

    response = superadmin.patch(f"{BASE}/{day['id']}", json={"is_open": False})

    assert response.status_code == 409
    assert "Refund" in response.json()["msg"]


# A day that's never been booked can be deleted; one that has can't.
def test_delete_only_never_booked(api: Api, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    end = dates + timedelta(days=1)
    _add(superadmin, service_id, dates, end)
    empty, booked = _overview(superadmin, service_id, dates, end)
    _book(api, customer, booked["id"])

    assert superadmin.delete(f"{BASE}/{empty['id']}").status_code == 200
    assert _overview(superadmin, service_id, dates, dates) == []

    response = superadmin.delete(f"{BASE}/{booked['id']}")
    assert response.status_code == 409
    assert "Close it instead" in response.json()["msg"]


# Admins see the days and their places but can't change them; families
# can't see the overview.
def test_admins_see_superadmins_change(admin, superadmin, customer, dates):
    service_id = _after_school(superadmin)
    _add(superadmin, service_id, dates, dates)
    day = _day(superadmin, service_id, dates)

    assert _overview(admin, service_id, dates, dates)[0]["id"] == day["id"]
    assert _add(admin, service_id, dates, dates).status_code == 403
    assert admin.patch(f"{BASE}/{day['id']}", json={"capacity": 5}).status_code == 403
    assert admin.delete(f"{BASE}/{day['id']}").status_code == 403
    assert customer.client.get(
        f"{BASE}/overview",
        params={"location_service_id": service_id, "date_from": dates.isoformat(), "date_to": dates.isoformat()},
    ).status_code == 403
