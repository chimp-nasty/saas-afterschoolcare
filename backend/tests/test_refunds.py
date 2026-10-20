"""
Refunding one booking (schema/0004): a pending refund goes to Stripe, and
the webhook settles it. Families can refund until refund_cutoff_days before
the session; staff and above until the end of the session day.
"""

from datetime import date

from app.errors.payments import PaymentProviderError
from tests.factories import Api


def _paid_booking(api: Api, customer, *, capacity: int = 30) -> tuple[dict, str]:
    """A new paid booking: returns (its review line, day id)."""
    child = api.new_child(customer)
    day = api.service_day(capacity=capacity)

    data = api.book(customer, {child["id"]: [day]}).json()["data"]
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    return _line(customer, data["booking_group_id"]), day


def _line(customer, group_id: str) -> dict:
    [line] = customer.client.get(f"/booking/v1/groups/{group_id}").json()["data"]["bookings"]

    return line


def _refund(client, booking_id: str):
    return client.post("/refunds/v1/", json={"booking_id": booking_id})


def _stripe_refund_id(fake_stripe, booking_id: str) -> str:
    [refund_id] = [
        refund_id
        for refund_id, refund in fake_stripe.state.refunds.items()
        if refund["metadata"]["booking_id"] == booking_id
    ]

    return refund_id


def _cutoff(api: Api, day_id: str) -> int:
    [(days,)] = api.sql(
        "SELECT lsc.refund_cutoff_days FROM public.location_service_config lsc "
        "JOIN public.location_service_days d ON d.location_service_id = lsc.location_service_id "
        "WHERE d.id = :day_id",
        day_id=day_id,
    )

    return days


def _set_cutoff(api: Api, day_id: str, days: int):
    api.sql(
        "UPDATE public.location_service_config lsc SET refund_cutoff_days = :days "
        "FROM public.location_service_days d "
        "WHERE d.id = :day_id AND lsc.location_service_id = d.location_service_id",
        days=days,
        day_id=day_id,
    )


def _days_until(api: Api, day_id: str) -> int:
    [(days,)] = api.sql(
        "SELECT d.service_date - (now() AT TIME ZONE l.timezone)::date "
        "FROM public.location_service_days d "
        "JOIN tenancy.locations l ON l.id = d.location_id "
        "WHERE d.id = :day_id",
        day_id=day_id,
    )

    return days


# ---------------------------------------------------------------------------
# Requesting
# ---------------------------------------------------------------------------

# A family can refund a paid session inside their window. It's pending until
# Stripe confirms, and the place stays held meanwhile.
def test_family_can_refund_inside_the_window(api: Api, customer, fake_stripe):
    line, _ = _paid_booking(api, customer)

    response = _refund(customer.client, line["id"])

    assert response.status_code == 201, response.text
    refund = response.json()["data"]
    assert refund["status"] == "PENDING"
    assert refund["amount_cents"] == line["price_snapshot_cents"]

    [stripe_refund] = fake_stripe.state.refunds.values()
    assert stripe_refund["amount_cents"] == line["price_snapshot_cents"]

    line = _line(customer, line["booking_group_id"])
    assert line["refund_status"] == "PENDING"
    assert line["is_refundable"] is False
    assert line["booking_status"] == "CONFIRMED"


# Only one refund at a time: asking again while the first is pending is
# refused (409), and the message says a refund was already requested rather
# than that the session can't be refunded.
def test_second_refund_refused_while_one_is_pending(api: Api, customer):
    line, _ = _paid_booking(api, customer)
    _refund(customer.client, line["id"])

    response = _refund(customer.client, line["id"])

    assert response.status_code == 409
    assert "already been requested" in response.json()["msg"]


# An unpaid booking has nothing to refund.
def test_unpaid_booking_cannot_be_refunded(api: Api, customer):
    child = api.new_child(customer)
    data = api.book(customer, {child["id"]: [api.service_day()]}).json()["data"]

    response = _refund(customer.client, _line(customer, data["booking_group_id"])["id"])

    assert response.status_code == 409


# A family can't refund another family's booking (404).
def test_cannot_refund_another_familys_booking(api: Api, customer, other_customer):
    line, _ = _paid_booking(api, customer)

    assert _refund(other_customer.client, line["id"]).status_code == 404


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

# Past the family's cutoff, the family can't refund, but staff still can.
def test_staff_can_refund_after_the_familys_cutoff(api: Api, customer, admin):
    line, day = _paid_booking(api, customer)
    original = _cutoff(api, day)

    # Make the family's cutoff a day past (the service is shared by every
    # test, so it's put back after).
    _set_cutoff(api, day, _days_until(api, day) + 1)
    try:
        response = _refund(customer.client, line["id"])
        assert response.status_code == 409
        assert "can't be refunded" in response.json()["msg"]

        assert _refund(admin, line["id"]).status_code == 201
    finally:
        _set_cutoff(api, day, original)


# Once the session day has passed, not even staff can refund it.
def test_staff_cannot_refund_after_the_session_day(api: Api, customer, admin):
    line, day = _paid_booking(api, customer)

    # Bookings can't be made for the past, so move the day afterwards. A
    # fixed date long before the dev seed's calendar can't clash with it.
    api.sql(
        "UPDATE public.location_service_days SET service_date = :service_date WHERE id = :id",
        service_date=date(2001, 1, 1),
        id=day,
    )

    assert _refund(admin, line["id"]).status_code == 409


# ---------------------------------------------------------------------------
# Settling (webhook)
# ---------------------------------------------------------------------------

# When Stripe confirms, the booking is cancelled and refunded, and its place
# is free for someone else.
def test_successful_refund_cancels_the_booking_and_frees_the_place(api: Api, customer, other_customer, fake_stripe):
    line, day = _paid_booking(api, customer, capacity=1)
    _refund(customer.client, line["id"])

    response = api.refund_webhook("refund.updated", _stripe_refund_id(fake_stripe, line["id"]), status="succeeded")
    assert response.status_code == 200

    line = _line(customer, line["booking_group_id"])
    assert line["refund_status"] == "SUCCEEDED"
    assert (line["booking_status"], line["payment_status"]) == ("CANCELLED", "REFUNDED")

    their_child = api.new_child(other_customer)
    assert api.book(other_customer, {their_child["id"]: [day]}).status_code == 201


# A failed refund is recorded, and the session can be refunded again.
def test_failed_refund_can_be_tried_again(api: Api, customer, fake_stripe):
    line, _ = _paid_booking(api, customer)
    _refund(customer.client, line["id"])

    api.refund_webhook("refund.failed", _stripe_refund_id(fake_stripe, line["id"]), status="failed")

    line = _line(customer, line["booking_group_id"])
    assert line["refund_status"] == "FAILED"
    assert line["booking_status"] == "CONFIRMED"
    assert line["is_refundable"] is True

    assert _refund(customer.client, line["id"]).status_code == 201


# Stripe repeats events, and can send a late "failed"; a completed refund
# stays completed.
def test_repeat_refund_webhooks_are_harmless(api: Api, customer, fake_stripe):
    line, _ = _paid_booking(api, customer)
    _refund(customer.client, line["id"])
    stripe_refund_id = _stripe_refund_id(fake_stripe, line["id"])

    api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded")
    assert api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded").status_code == 200
    assert api.refund_webhook("refund.failed", stripe_refund_id, status="failed").status_code == 200

    assert _line(customer, line["booking_group_id"])["refund_status"] == "SUCCEEDED"


# Refunds made by hand in the Stripe dashboard (no metadata of ours) are
# acknowledged and ignored, so Stripe doesn't keep retrying them.
def test_dashboard_refunds_are_ignored(api: Api):
    response = api.refund_webhook("refund.updated", "re_dashboard", status="succeeded", metadata={})

    assert response.status_code == 200


# If Stripe is down, the request fails with a 502 and the refund is
# recorded as failed, so it can be tried again.
def test_stripe_failure_leaves_a_refund_that_can_be_retried(api: Api, customer, fake_stripe, monkeypatch):
    line, _ = _paid_booking(api, customer)

    def stripe_down(_self, **_):
        raise PaymentProviderError(log_reason="Stripe unavailable")

    # Restored by hand: monkeypatch.undo() would also undo conftest's
    # FakeStripe patches.
    working = fake_stripe.create_refund
    monkeypatch.setattr(fake_stripe, "create_refund", stripe_down)
    response = _refund(customer.client, line["id"])
    monkeypatch.setattr(fake_stripe, "create_refund", working)

    assert response.status_code == 502
    assert _line(customer, line["booking_group_id"])["refund_status"] == "FAILED"

    assert _refund(customer.client, line["id"]).status_code == 201
