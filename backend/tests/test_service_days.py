"""
What the booking calendar knows about each service day: places left (every
family's bookings counted), which of your own children are already booked,
and whether the day has passed.
"""

from tests.factories import Api


def _day(client, day_id: str) -> dict:
    days = client.get("/location-service-days/v1/").json()["data"]

    return next(day for day in days if day["id"] == day_id)


# Places left counts every family's live bookings, not just your own, so a
# family can see a day filling up before they try to book it.
def test_places_left_counts_every_family(api: Api, customer, other_customer):
    day = api.service_day(capacity=3)
    their_child = api.new_child(other_customer)

    api.book(other_customer, {their_child["id"]: [day]})

    assert _day(customer.client, day)["places_left"] == 2


# Cancelled bookings and lapsed holds give their place back.
def test_cancelled_and_lapsed_bookings_free_their_place(api: Api, customer, other_customer):
    day = api.service_day(capacity=3)
    their_child = api.new_child(other_customer)

    cancelled = api.book(other_customer, {their_child["id"]: [day]}).json()["data"]
    other_customer.client.post(f"/booking/v1/groups/{cancelled['booking_group_id']}/cancel")

    lapsed = api.book(other_customer, {api.new_child(other_customer)["id"]: [day]}).json()["data"]
    api.sql(
        "UPDATE public.bookings SET created_at = now() - interval '2 hours' WHERE booking_group_id = :id",
        id=lapsed["booking_group_id"],
    )

    assert _day(customer.client, day)["places_left"] == 3


# Your own booked children are listed for the day (so the calendar can mark
# it), and never another family's.
def test_booked_children_are_only_your_own(api: Api, customer, other_customer):
    day = api.service_day()
    child = api.new_child(customer)

    api.book(customer, {child["id"]: [day]})

    assert _day(customer.client, day)["booked_child_ids"] == [child["id"]]
    assert _day(other_customer.client, day)["booked_child_ids"] == []


# Today and earlier are marked as past (they can't be booked); future days
# aren't.
def test_past_days_are_marked(api: Api, customer):
    today = api.service_day(days_from_today=0)
    future = api.service_day()

    assert _day(customer.client, today)["is_past"] is True
    assert _day(customer.client, future)["is_past"] is False
