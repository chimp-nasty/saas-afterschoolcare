"""
The review screen for a pending booking group: view it, continue to
payment, or cancel. Plus the lapsed-hold backstop (schema/0009).
"""

from tests.factories import Api


def _pending_group(api: Api, customer, *, capacity: int = 30):
    """A new pending booking; returns (create response data, day id)."""
    child = api.new_child(customer)
    day = api.service_day(capacity=capacity)

    response = api.book(customer, {child["id"]: [day]})
    assert response.status_code == 201, response.text

    return response.json()["data"], day


def _group(customer, group_id: str):
    return customer.client.get(f"/booking/v1/groups/{group_id}")


def _lapse_hold(api: Api, group_id: str):
    """Pretend the checkout was abandoned long ago and its webhook lost."""
    api.sql(
        "UPDATE public.bookings SET created_at = now() - interval '2 hours' "
        "WHERE booking_group_id = :group_id",
        group_id=group_id,
    )


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

def test_view_pending_group(api: Api, customer):
    data, _ = _pending_group(api, customer)

    response = _group(customer, data["booking_group_id"])

    assert response.status_code == 200
    group = response.json()["data"]
    assert group["status"] == "PENDING"
    assert group["total_cents"] == data["amount"]
    assert [b["price_snapshot_cents"] for b in group["bookings"]] == [data["amount"]]


def test_cannot_view_another_customers_group(api: Api, customer, other_customer):
    data, _ = _pending_group(api, customer)

    assert _group(other_customer, data["booking_group_id"]).status_code == 404


# ---------------------------------------------------------------------------
# Continue to payment
# ---------------------------------------------------------------------------

def test_continue_returns_the_open_checkout(api: Api, customer):
    data, _ = _pending_group(api, customer)

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 200
    assert response.json()["data"]["checkout_url"] == data["checkout_url"]


def test_continue_after_stripe_expired_starts_a_new_checkout(api: Api, customer, fake_stripe):
    data, _ = _pending_group(api, customer)
    fake_stripe.state.sessions[api.session_id(data["checkout_url"])].status = "expired"

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 200
    assert response.json()["data"]["checkout_url"] != data["checkout_url"]


def test_cannot_continue_a_paid_group(api: Api, customer):
    data, _ = _pending_group(api, customer)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 400


def test_cannot_continue_another_customers_group(api: Api, customer, other_customer):
    data, _ = _pending_group(api, customer)

    response = other_customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def test_cancel_releases_the_place_and_closes_checkout(api: Api, customer, other_customer, fake_stripe):
    data, day = _pending_group(api, customer, capacity=1)

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/cancel"
    )

    assert response.status_code == 200
    assert _group(customer, data["booking_group_id"]).json()["data"]["status"] == "CANCELLED"

    # The Stripe session can no longer be paid...
    assert fake_stripe.state.sessions[api.session_id(data["checkout_url"])].status == "expired"

    # ...and the place is free again.
    their_child = api.new_child(other_customer)
    assert api.book(other_customer, {their_child["id"]: [day]}).status_code == 201


def test_cannot_cancel_a_paid_group(api: Api, customer):
    data, _ = _pending_group(api, customer)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/cancel"
    )

    assert response.status_code == 400
    assert _group(customer, data["booking_group_id"]).json()["data"]["status"] == "CONFIRMED"


def test_cannot_cancel_once_paid_on_stripe(api: Api, customer, fake_stripe):
    # Paid on Stripe, but the webhook hasn't arrived yet.
    data, _ = _pending_group(api, customer)
    fake_stripe.state.sessions[api.session_id(data["checkout_url"])].status = "complete"

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/cancel"
    )

    assert response.status_code == 400
    assert _group(customer, data["booking_group_id"]).json()["data"]["status"] == "PENDING"


def test_cancel_twice(api: Api, customer):
    data, _ = _pending_group(api, customer)
    url = f"/booking/v1/groups/{data['booking_group_id']}/cancel"

    assert customer.client.post(url).status_code == 200
    assert customer.client.post(url).status_code == 409


def test_cannot_cancel_another_customers_group(api: Api, customer, other_customer):
    data, _ = _pending_group(api, customer)

    response = other_customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/cancel"
    )

    assert response.status_code == 404
    assert _group(customer, data["booking_group_id"]).json()["data"]["status"] == "PENDING"


# ---------------------------------------------------------------------------
# Lapsed holds (schema/0009): a missed expiry webhook can't hold places
# ---------------------------------------------------------------------------

def test_lapsed_hold_reads_as_expired(api: Api, customer):
    data, _ = _pending_group(api, customer)
    _lapse_hold(api, data["booking_group_id"])

    group = _group(customer, data["booking_group_id"]).json()["data"]
    pending = customer.client.get(
        "/booking/v1/", params={"booking_status": "PENDING"}
    ).json()["data"]

    assert group["status"] == "EXPIRED"
    assert pending == []


def test_lapsed_hold_cannot_be_paid(api: Api, customer):
    data, _ = _pending_group(api, customer)
    _lapse_hold(api, data["booking_group_id"])

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 409


def test_lapsed_hold_frees_its_place(api: Api, customer, other_customer):
    data, day = _pending_group(api, customer, capacity=1)
    _lapse_hold(api, data["booking_group_id"])

    their_child = api.new_child(other_customer)

    assert api.book(other_customer, {their_child["id"]: [day]}).status_code == 201


def test_lapsed_hold_does_not_block_rebooking_the_same_child(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()

    first = api.book(customer, {child["id"]: [day]}).json()["data"]
    _lapse_hold(api, first["booking_group_id"])

    assert api.book(customer, {child["id"]: [day]}).status_code == 201


def test_payment_after_the_hold_lapsed_keeps_bookings_released(api: Api, customer, other_customer):
    # The worst case the hold length guards against: the place was given
    # away before a late payment's webhook arrived. The bookings stay
    # released (the webhook logs that a refund is needed).
    data, day = _pending_group(api, customer, capacity=1)
    _lapse_hold(api, data["booking_group_id"])

    their_child = api.new_child(other_customer)
    api.book(other_customer, {their_child["id"]: [day]})

    session_id = api.session_id(data["checkout_url"])
    assert api.webhook("checkout.session.completed", session_id).status_code == 200

    status = customer.client.get(f"/booking/v1/checkout/{session_id}").json()["data"]
    assert status["payment_status"] == "SUCCEEDED"
    assert status["bookings"][0]["booking_status"] == "EXPIRED"


def test_cannot_pay_after_clearing_profile(api: Api, customer):
    data, _ = _pending_group(api, customer)
    url = f"/booking/v1/groups/{data['booking_group_id']}/checkout"

    customer.client.patch("/customer/v1/profile", json={"phone": None})
    response = customer.client.post(url)

    assert response.status_code == 400
    assert "Missing: phone" in response.json()["msg"]

    # Completing it again lets them pay.
    customer.client.patch("/customer/v1/profile", json={"phone": "0400000000"})
    assert customer.client.post(url).status_code == 200
