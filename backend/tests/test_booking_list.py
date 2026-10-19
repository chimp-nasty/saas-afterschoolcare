"""
"My bookings": one summary per booking group (checkout), upcoming first.
"""

from datetime import date

from tests.factories import Api


def _groups(customer, **params) -> list[dict]:
    response = customer.client.get("/booking/v1/groups", params=params)
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _book(api: Api, customer, selections: dict[str, list[str]]) -> str:
    response = api.book(customer, selections)
    assert response.status_code == 201, response.text

    return response.json()["data"]["booking_group_id"]


def _move_day_to(api: Api, day_id: str, service_date: date):
    # Bookings can't be made for the past, so make it past afterwards.
    api.sql(
        "UPDATE public.location_service_days SET service_date = :service_date WHERE id = :id",
        service_date=service_date,
        id=day_id,
    )


# 'My bookings' shows one summary per checkout covering all of it: both
# children's names, the first and last dates, the session count (3) and the
# total price.
def test_summary_covers_the_whole_checkout(api: Api, customer):
    emma = api.new_child(customer, first_name="Emma", last_name="Summary")
    noah = api.new_child(customer, first_name="Noah", last_name="Summary")
    first_day, second_day = api.service_day(), api.service_day()

    group_id = _book(api, customer, {emma["id"]: [first_day, second_day], noah["id"]: [first_day]})

    [group] = _groups(customer)
    days = dict(api.sql(
        "SELECT id::text, service_date FROM public.location_service_days WHERE id IN (:a, :b)",
        a=first_day, b=second_day,
    ))

    assert group["booking_group_id"] == group_id
    assert group["status"] == "PENDING"
    assert group["service_name"] == "After School Care"
    assert group["child_names"] == ["Emma Summary", "Noah Summary"]
    assert group["booking_count"] == 3
    assert group["total_cents"] == 3 * 3000
    assert group["first_date"] == days[first_day].isoformat()
    assert group["last_date"] == days[second_day].isoformat()


# With no tab filter, the list shows upcoming bookings first (soonest
# first), then past bookings (most recent first).
def test_upcoming_first_then_past(api: Api, customer):
    child = api.new_child(customer)

    # Factory days are in the future and get later with each call.
    soon_day, later_day, recent_day, old_day = (api.service_day() for _ in range(4))
    soon, later, recent, old = (
        _book(api, customer, {child["id"]: [day]})
        for day in (soon_day, later_day, recent_day, old_day)
    )

    # Fixed dates long before the dev seed's calendar, so they can't clash
    # with a seeded day for the same service.
    _move_day_to(api, recent_day, date(2000, 3, 1))
    _move_day_to(api, old_day, date(2000, 1, 1))

    order = [group["booking_group_id"] for group in _groups(customer)]

    assert order == [soon, later, recent, old]


# The Upcoming tab only shows bookings still to come that are pending or
# confirmed. History shows everything else: cancelled, expired (lapsed hold)
# and past bookings. With no tab filter, all four show.
def test_upcoming_and_history_scopes(api: Api, customer):
    child = api.new_child(customer)
    upcoming, cancelled, lapsed, past = (
        _book(api, customer, {child["id"]: [api.service_day()]})
        for _ in range(4)
    )

    customer.client.post(f"/booking/v1/groups/{cancelled}/cancel")
    api.sql(
        "UPDATE public.bookings SET created_at = now() - interval '2 hours' WHERE booking_group_id = :id",
        id=lapsed,
    )
    [(past_day,)] = api.sql(
        "SELECT location_service_day_id::text FROM public.bookings WHERE booking_group_id = :id",
        id=past,
    )
    _move_day_to(api, past_day, date(2000, 2, 1))

    def ids(**params) -> set[str]:
        return {g["booking_group_id"] for g in _groups(customer, **params)}

    assert ids(scope="upcoming") == {upcoming}
    assert ids(scope="history") == {cancelled, lapsed, past}
    assert ids() == {upcoming, cancelled, lapsed, past}


# The bookings list splits into pages: with two per page, three bookings
# come back as two then one, with no booking on both pages.
def test_list_paginates(api: Api, customer):
    child = api.new_child(customer)
    for _ in range(3):
        _book(api, customer, {child["id"]: [api.service_day()]})

    first = _groups(customer, page=1, limit=2)
    second = _groups(customer, page=2, limit=2)

    assert len(first) == 2
    assert len(second) == 1
    assert {g["booking_group_id"] for g in first}.isdisjoint(g["booking_group_id"] for g in second)


# The list reports each booking's real status: a cancelled one shows
# CANCELLED, and an unpaid one whose hold has run out shows EXPIRED.
def test_list_shows_cancelled_and_lapsed_status(api: Api, customer):
    child = api.new_child(customer)
    cancelled = _book(api, customer, {child["id"]: [api.service_day()]})
    lapsed = _book(api, customer, {child["id"]: [api.service_day()]})

    customer.client.post(f"/booking/v1/groups/{cancelled}/cancel")
    api.sql(
        "UPDATE public.bookings SET created_at = now() - interval '2 hours' WHERE booking_group_id = :id",
        id=lapsed,
    )

    statuses = {g["booking_group_id"]: g["status"] for g in _groups(customer)}

    assert statuses == {cancelled: "CANCELLED", lapsed: "EXPIRED"}


# A customer never sees another customer's bookings in their list.
def test_list_is_private(api: Api, customer, other_customer):
    child = api.new_child(customer)
    _book(api, customer, {child["id"]: [api.service_day()]})

    assert _groups(other_customer) == []
