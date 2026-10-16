import uuid

from tests.factories import Api


# Matches the dev seed's after_school_care price at location1.
AFTER_SCHOOL_CARE_CENTS = 3000


def test_create_booking(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()

    response = api.book(customer, {child["id"]: [day]})

    assert response.status_code == 201, response.text
    assert response.json()["data"]["amount"] == AFTER_SCHOOL_CARE_CENTS


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


def test_duplicate_booking(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()

    api.book(customer, {child["id"]: [day]})
    response = api.book(customer, {child["id"]: [day]})

    assert response.status_code == 409


def test_cannot_book_another_familys_child(api: Api, customer, other_customer):
    their_child = api.new_child(other_customer)
    day = api.service_day()

    response = api.book(customer, {their_child["id"]: [day]})

    assert response.status_code == 400


def test_capacity_is_enforced(api: Api, customer):
    first = api.new_child(customer)
    second = api.new_child(customer)
    day = api.service_day(capacity=1)

    response = api.book(customer, {first["id"]: [day], second["id"]: [day]})

    assert response.status_code == 409
    assert "No capacity available" in response.json()["msg"]


def test_one_service_per_booking(api: Api, customer):
    child = api.new_child(customer)
    after_school = api.service_day(service="after_school_care")
    before_school = api.service_day(service="before_school_care")

    response = api.book(customer, {child["id"]: [after_school, before_school]})

    assert response.status_code == 400


def test_unknown_service_day(api: Api, customer):
    child = api.new_child(customer)

    response = api.book(customer, {child["id"]: [str(uuid.uuid4())]})

    assert response.status_code == 400


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
        params={"limit": 1},
    ).json()["data"]

    assert len(pending) == 2
    assert confirmed == []
    assert len(first_page) == 1


def test_list_bookings_rejects_unknown_status(customer):
    response = customer.client.get(
        "/booking/v1/",
        params={"booking_status": "NOT_A_STATUS"},
    )

    assert response.status_code == 422


def test_get_booking(api: Api, customer):
    child = api.new_child(customer)
    api.book(customer, {child["id"]: [api.service_day()]})
    [booking] = customer.client.get("/booking/v1/").json()["data"]

    response = customer.client.get(f"/booking/v1/{booking['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["price_snapshot_cents"] == AFTER_SCHOOL_CARE_CENTS


def test_get_unknown_booking(customer):
    response = customer.client.get(
        "/booking/v1/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
