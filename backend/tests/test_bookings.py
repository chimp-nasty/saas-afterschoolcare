import uuid

from tests.factories import Api


# Matches the dev seed's after_school_care price at location1.
AFTER_SCHOOL_CARE_CENTS = 3000


# A customer can book a day for their child, charged at the service's price
# (3000 cents).
def test_create_booking(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()

    response = api.book(customer, {child["id"]: [day]})

    assert response.status_code == 201, response.text
    assert response.json()["data"]["amount"] == AFTER_SCHOOL_CARE_CENTS


# Sending the same booking twice with the same idempotency key (e.g. a
# double-click or retry) returns the original booking instead of making a
# second one.
def test_same_idempotency_key_resumes_booking(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()
    key = uuid.uuid4().hex

    first = api.book(customer, {child["id"]: [day]}, idempotency_key=key)
    second = api.book(customer, {child["id"]: [day]}, idempotency_key=key)

    assert second.status_code == 201
    assert (
        second.json()["data"]["booking_group_id"]
        == first.json()["data"]["booking_group_id"]
    )


# The same child can't be booked twice for the same day (409).
def test_duplicate_booking(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()

    api.book(customer, {child["id"]: [day]})
    response = api.book(customer, {child["id"]: [day]})

    assert response.status_code == 409


# A customer can't book a child that belongs to another customer (400).
def test_cannot_book_another_familys_child(api: Api, customer, other_customer):
    their_child = api.new_child(other_customer)
    day = api.service_day()

    response = api.book(customer, {their_child["id"]: [day]})

    assert response.status_code == 400
    assert response.json()["msg"] == "Invalid child for this booking"


# A day can't be overbooked: booking two children into a day with one place
# left is refused with 'No capacity available'.
def test_capacity_is_enforced(api: Api, customer):
    first = api.new_child(customer)
    second = api.new_child(customer)
    day = api.service_day(capacity=1)

    response = api.book(customer, {first["id"]: [day], second["id"]: [day]})

    assert response.status_code == 409
    assert "No capacity available" in response.json()["msg"]


# One booking can only cover one service: mixing after-school and before-
# school care days is refused (400).
def test_one_service_per_booking(api: Api, customer):
    child = api.new_child(customer)
    after_school = api.service_day(service="after_school_care")
    before_school = api.service_day(service="before_school_care")

    response = api.book(customer, {child["id"]: [after_school, before_school]})

    assert response.status_code == 400
    assert response.json()["msg"] == "Multiple Services selected"


# Booking a service day that doesn't exist is refused (400).
def test_unknown_service_day(api: Api, customer):
    child = api.new_child(customer)

    response = api.book(customer, {child["id"]: [str(uuid.uuid4())]})

    assert response.status_code == 400
    assert response.json()["msg"] == "Invalid service day"


# The conflicts check, used before booking, reports a child already booked
# on a chosen day, with the child's name and the day.
def test_conflicts_preview(api: Api, customer):
    child = api.new_child(customer, first_name="Noah", last_name="Preview")
    day = api.service_day()
    api.book(customer, {child["id"]: [day]})

    response = customer.client.post(
        "/booking/v1/conflicts",
        json={
            "idempotency_key": uuid.uuid4().hex,
            "bookings": [{"child_id": child["id"], "location_service_days": [day]}],
        },
    )

    assert response.status_code == 200
    [conflict] = response.json()["data"]
    assert conflict["child_name"] == "Noah Preview"
    assert conflict["location_service_day_id"] == day


# The individual bookings list filters by status (two PENDING, no CONFIRMED)
# and splits into pages: one per page gives two pages with different
# bookings.
def test_list_bookings_filters_and_paginates(api: Api, customer):
    child = api.new_child(customer)
    api.book(customer, {child["id"]: [api.service_day()]})
    api.book(customer, {child["id"]: [api.service_day()]})

    pending = customer.client.get(
        "/booking/v1/",
        params={"booking_status": "PENDING"},
    ).json()["data"]
    confirmed = customer.client.get(
        "/booking/v1/",
        params={"booking_status": "CONFIRMED"},
    ).json()["data"]
    first_page = customer.client.get(
        "/booking/v1/",
        params={"page": 1, "limit": 1},
    ).json()["data"]
    second_page = customer.client.get(
        "/booking/v1/",
        params={"page": 2, "limit": 1},
    ).json()["data"]

    assert len(pending) == 2
    assert confirmed == []
    assert len(first_page) == 1
    assert len(second_page) == 1
    assert first_page[0]["id"] != second_page[0]["id"]


# Filtering bookings by a status that doesn't exist is rejected as invalid
# (422).
def test_list_bookings_rejects_unknown_status(customer):
    response = customer.client.get(
        "/booking/v1/",
        params={"booking_status": "NOT_A_STATUS"},
    )

    assert response.status_code == 422


# A customer can fetch one of their bookings by id, and it carries the price
# at the time of booking.
def test_get_booking(api: Api, customer):
    child = api.new_child(customer)
    api.book(customer, {child["id"]: [api.service_day()]})
    [booking] = customer.client.get("/booking/v1/").json()["data"]

    response = customer.client.get(f"/booking/v1/{booking['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["price_snapshot_cents"] == AFTER_SCHOOL_CARE_CENTS


# Fetching a booking that doesn't exist returns 404.
def test_get_unknown_booking(customer):
    response = customer.client.get(
        "/booking/v1/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Rules enforced by the trg_bookings_enforce_rules trigger (schema/0008)
# ---------------------------------------------------------------------------

# Days in the past can't be booked.
def test_cannot_book_a_past_day(api: Api, customer):
    child = api.new_child(customer)
    yesterday = api.service_day(days_from_today=-1)

    response = api.book(customer, {child["id"]: [yesterday]})

    assert response.status_code == 400
    assert response.json()["msg"] == "Bookings must be for a future date"


# Today can't be booked either; bookings must be for a future date.
def test_cannot_book_today(api: Api, customer):
    child = api.new_child(customer)
    today = api.service_day(days_from_today=0)

    response = api.book(customer, {child["id"]: [today]})

    assert response.status_code == 400
    assert response.json()["msg"] == "Bookings must be for a future date"


# A day the location has marked closed can't be booked.
def test_cannot_book_a_closed_day(api: Api, customer):
    child = api.new_child(customer)
    closed = api.service_day(is_open=False)

    response = api.book(customer, {child["id"]: [closed]})

    assert response.status_code == 400
    assert response.json()["msg"] == "This service day is closed"


# A child with medical info is held for staff review and can't be booked
# until it's approved.
def test_cannot_book_a_child_awaiting_medical_review(api: Api, customer):
    child = api.new_child(customer, medical_info="Asthma")
    assert child["review_status"] == "pending"

    response = api.book(customer, {child["id"]: [api.service_day()]})

    assert response.status_code == 400
    assert "awaiting medical review" in response.json()["msg"]


# ---------------------------------------------------------------------------
# A complete customer profile is required to book
# ---------------------------------------------------------------------------

# A customer whose profile became incomplete (phone removed) can't book, and
# is told what's missing.
def test_cannot_book_after_clearing_profile(api: Api, customer):
    # The profile was complete when the child was added, then cleared.
    child = api.new_child(customer)
    customer.client.patch("/customer/v1/profile", json={"phone": None})

    response = api.book(customer, {child["id"]: [api.service_day()]})

    assert response.status_code == 400
    assert "Missing: phone" in response.json()["msg"]


# A customer who never completed their profile can't book, even for a child
# added behind the scenes, and is told every missing field.
def test_cannot_book_without_ever_having_a_profile(api: Api):
    # A child inserted directly (as the dev seed does), bypassing the
    # complete-profile check on adding a child. Its medical review state is
    # created by trg_child_profile_medical_review.
    customer = api.new_customer(complete_profile=False)

    [(child_id,)] = api.sql(
        """
        INSERT INTO public.child_profile (location_id, user_id, first_name, last_name, dob)
        SELECT lur.location_id, u.id, 'Seeded', 'Child', DATE '2016-01-01'
        FROM auth.users u
        JOIN auth.location_user_roles lur ON lur.user_id = u.id
        WHERE u.email = :email
        RETURNING id
        """,
        email=customer.email,
    )

    response = api.book(customer, {str(child_id): [api.service_day()]})

    assert response.status_code == 400
    assert response.json()["msg"] == (
        "Customer profile is incomplete. "
        "Missing: phone, address_line_1, suburb, state, postcode, emergency_contact"
    )
