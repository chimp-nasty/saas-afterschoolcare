"""
The review screen for a booking group: view it, continue to payment, or
cancel a pending one; see which paid days can be refunded. Plus the
lapsed-hold backstop (schema/0009).
"""

from contextlib import contextmanager
from datetime import date, timedelta

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

# The review page for a new, unpaid booking shows it as PENDING with the
# right total and per-session price.
def test_view_pending_group(api: Api, customer):
    data, _ = _pending_group(api, customer)

    response = _group(customer, data["booking_group_id"])

    assert response.status_code == 200
    group = response.json()["data"]
    assert group["status"] == "PENDING"
    assert group["total_cents"] == data["amount"]
    assert [b["price_snapshot_cents"] for b in group["bookings"]] == [data["amount"]]


# A customer can't open another customer's booking review page (404).
def test_cannot_view_another_customers_group(api: Api, customer, other_customer):
    data, _ = _pending_group(api, customer)

    assert _group(other_customer, data["booking_group_id"]).status_code == 404


# ---------------------------------------------------------------------------
# Continue to payment
# ---------------------------------------------------------------------------

# 'Continue to payment' on an unpaid booking reuses the Stripe checkout
# that's already open instead of making a new one.
def test_continue_returns_the_open_checkout(api: Api, customer):
    data, _ = _pending_group(api, customer)

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 200
    assert response.json()["data"]["checkout_url"] == data["checkout_url"]


# If Stripe has already expired the old checkout, 'Continue to payment'
# opens a fresh one with a different link.
def test_continue_after_stripe_expired_starts_a_new_checkout(api: Api, customer, fake_stripe):
    data, _ = _pending_group(api, customer)
    fake_stripe.state.sessions[api.session_id(data["checkout_url"])].status = "expired"

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 200
    assert response.json()["data"]["checkout_url"] != data["checkout_url"]


# A booking that's already paid can't be sent to checkout again (400).
def test_cannot_continue_a_paid_group(api: Api, customer):
    data, _ = _pending_group(api, customer)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 400
    assert response.json()["msg"] == "Booking group is already marked as paid"


# A customer can't start checkout for another customer's booking (404).
def test_cannot_continue_another_customers_group(api: Api, customer, other_customer):
    data, _ = _pending_group(api, customer)

    response = other_customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

# Cancelling an unpaid booking marks it CANCELLED, expires its Stripe
# checkout so it can't be paid, and frees the place for someone else.
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


# A paid (confirmed) booking can't be cancelled this way (400) and stays
# CONFIRMED.
def test_cannot_cancel_a_paid_group(api: Api, customer):
    data, _ = _pending_group(api, customer)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/cancel"
    )

    assert response.status_code == 400
    assert _group(customer, data["booking_group_id"]).json()["data"]["status"] == "CONFIRMED"


# If the customer has paid on Stripe but the webhook hasn't arrived yet,
# cancelling is refused, so the money isn't taken for a cancelled booking,
# and the payment is confirmed there and then.
def test_cannot_cancel_once_paid_on_stripe(api: Api, customer):
    # Paid on Stripe, but the webhook hasn't arrived yet.
    data, _ = _pending_group(api, customer)
    api.pay_at_stripe(api.session_id(data["checkout_url"]))

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/cancel"
    )

    assert response.status_code == 400
    assert _group(customer, data["booking_group_id"]).json()["data"]["status"] == "CONFIRMED"


# Cancelling works once; cancelling the same booking again is refused as a
# conflict (409).
def test_cancel_twice(api: Api, customer):
    data, _ = _pending_group(api, customer)
    url = f"/booking/v1/groups/{data['booking_group_id']}/cancel"

    assert customer.client.post(url).status_code == 200
    assert customer.client.post(url).status_code == 409


# A customer can't cancel another customer's booking (404), and the booking
# is left PENDING.
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

# An unpaid booking whose hold has run out (Stripe's expiry webhook was
# missed) shows as EXPIRED, and no longer appears when filtering for PENDING
# bookings.
def test_lapsed_hold_reads_as_expired(api: Api, customer):
    data, _ = _pending_group(api, customer)
    _lapse_hold(api, data["booking_group_id"])

    group = _group(customer, data["booking_group_id"]).json()["data"]
    pending = customer.client.get(
        "/booking/v1/", params={"booking_status": "PENDING"}
    ).json()["data"]

    assert group["status"] == "EXPIRED"
    assert pending == []


# An unpaid booking whose hold has run out can't be sent to checkout (409).
def test_lapsed_hold_cannot_be_paid(api: Api, customer):
    data, _ = _pending_group(api, customer)
    _lapse_hold(api, data["booking_group_id"])

    response = customer.client.post(
        f"/booking/v1/groups/{data['booking_group_id']}/checkout"
    )

    assert response.status_code == 409


# A hold that has run out no longer takes up a place: another customer can
# book the last spot.
def test_lapsed_hold_frees_its_place(api: Api, customer, other_customer):
    data, day = _pending_group(api, customer, capacity=1)
    _lapse_hold(api, data["booking_group_id"])

    their_child = api.new_child(other_customer)

    assert api.book(other_customer, {their_child["id"]: [day]}).status_code == 201


# A hold that has run out doesn't stop the same child being booked again for
# the same day.
def test_lapsed_hold_does_not_block_rebooking_the_same_child(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()

    first = api.book(customer, {child["id"]: [day]}).json()["data"]
    _lapse_hold(api, first["booking_group_id"])

    assert api.book(customer, {child["id"]: [day]}).status_code == 201


# If a payment arrives after the hold ran out and the place was given away,
# the payment is recorded but the bookings stay EXPIRED (the webhook logs
# that a refund is needed).
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


# A customer can't pay while their profile is incomplete (missing phone);
# once they fill it in again, checkout works.
def test_cannot_pay_after_clearing_profile(api: Api, customer):
    data, _ = _pending_group(api, customer)
    url = f"/booking/v1/groups/{data['booking_group_id']}/checkout"

    customer.client.patch("/customer/v1/profile", json={"phone": None})
    response = customer.client.post(url)

    assert response.status_code == 400
    assert "Missing: phone" in response.json()["msg"]

    # Completing it again lets them pay.
    customer.client.patch("/customer/v1/profile", json={"phone": customer.phone})
    assert customer.client.post(url).status_code == 200


# ---------------------------------------------------------------------------
# Refund window (location_service_config.refund_cutoff_days, schema/0004)
# ---------------------------------------------------------------------------

def _paid_group(api: Api, customer):
    data, day = _pending_group(api, customer)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    return data, day


def _line(customer, group_id: str) -> dict:
    [line] = _group(customer, group_id).json()["data"]["bookings"]

    return line


def _days_until(api: Api, day_id: str) -> int:
    """Days from today (location time) to the day's session."""
    [(days,)] = api.sql(
        "SELECT d.service_date - (now() AT TIME ZONE l.timezone)::date "
        "FROM public.location_service_days d "
        "JOIN tenancy.locations l ON l.id = d.location_id "
        "WHERE d.id = :day_id",
        day_id=day_id,
    )

    return days


@contextmanager
def _refund_cutoff(api: Api, day_id: str, days: int):
    """
    Set the cutoff on the day's service for one test, then put it back
    (the service is shared by every test).
    """
    [(original,)] = api.sql(
        "SELECT lsc.refund_cutoff_days "
        "FROM public.location_service_config lsc "
        "JOIN public.location_service_days d ON d.location_service_id = lsc.location_service_id "
        "WHERE d.id = :day_id",
        day_id=day_id,
    )
    set_cutoff = (
        "UPDATE public.location_service_config lsc SET refund_cutoff_days = :days "
        "FROM public.location_service_days d "
        "WHERE d.id = :day_id AND lsc.location_service_id = d.location_service_id"
    )

    api.sql(set_cutoff, days=days, day_id=day_id)
    try:
        yield
    finally:
        api.sql(set_cutoff, days=original, day_id=day_id)


# A paid session can be refunded, and with the default 2-day cutoff its last
# refundable day is two days before the session.
def test_paid_day_is_refundable_until_two_days_before(api: Api, customer):
    data, _ = _paid_group(api, customer)

    line = _line(customer, data["booking_group_id"])

    assert line["is_refundable"] is True
    assert line["refundable_until"] == (
        date.fromisoformat(line["service_date"]) - timedelta(days=2)
    ).isoformat()


# The cutoff day itself is still refundable (until 11:59pm, location time);
# once it's passed, the session is no longer refundable.
def test_refund_window_closes_after_the_cutoff_day(api: Api, customer):
    data, day = _paid_group(api, customer)
    days = _days_until(api, day)

    # The cutoff day itself is still refundable (until 11:59pm)...
    with _refund_cutoff(api, day, days):
        assert _line(customer, data["booking_group_id"])["is_refundable"] is True

    # ...the day after it isn't.
    with _refund_cutoff(api, day, days + 1):
        assert _line(customer, data["booking_group_id"])["is_refundable"] is False


# Unpaid (pending) and cancelled sessions are never refundable.
def test_only_paid_days_are_refundable(api: Api, customer):
    pending, _ = _pending_group(api, customer)
    cancelled, _ = _pending_group(api, customer)
    customer.client.post(f"/booking/v1/groups/{cancelled['booking_group_id']}/cancel")

    assert _line(customer, pending["booking_group_id"])["is_refundable"] is False
    assert _line(customer, cancelled["booking_group_id"])["is_refundable"] is False
