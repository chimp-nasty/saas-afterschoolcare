"""
Stripe checkout: creating a booking opens a checkout session, and only the
webhook moves payment state (see tests.factories.FakeStripe).
"""

import uuid

from app.core.config import settings
from tests.factories import Api


def _booked(api: Api, customer, *, capacity: int = 30, key: str | None = None):
    """Book one new day for a new child; returns (response json data, day id)."""
    child = api.new_child(customer)
    day = api.service_day(capacity=capacity)

    response = api.book(customer, {child["id"]: [day]}, idempotency_key=key)
    assert response.status_code == 201, response.text

    return response.json()["data"], day


def _status(customer, session_id: str) -> dict:
    response = customer.client.get(f"/booking/v1/checkout/{session_id}")
    assert response.status_code == 200, response.text

    return response.json()["data"]


def test_booking_opens_a_checkout(api: Api, customer, fake_stripe):
    data, _ = _booked(api, customer)

    assert data["checkout_url"].startswith("https://checkout.stripe.test/")

    created = fake_stripe.state.created[-1]
    site = f"https://tenant1.{settings.BASE_DOMAIN}/location1"
    assert created["success_url"] == f"{site}/bookings/success?session_id={{CHECKOUT_SESSION_ID}}"
    assert created["cancel_url"] == f"{site}/bookings/new"
    assert [item.amount_cents for item in created["line_items"]] == [data["amount"]]


def test_checkout_rejects_another_sites_origin(api: Api, customer):
    child = api.new_child(customer)

    response = customer.client.post(
        "/booking/v1/",
        headers={"Origin": "https://evil.example.com"},
        json={
            "idempotency_key": uuid.uuid4().hex,
            "bookings": [{"child_id": child["id"], "location_service_days": [api.service_day()]}],
        },
    )

    assert response.status_code == 400


def test_new_checkout_is_pending(api: Api, customer):
    data, _ = _booked(api, customer)

    status = _status(customer, api.session_id(data["checkout_url"]))

    assert status["payment_status"] == "PENDING"
    assert status["total_cents"] == data["amount"]
    assert [b["booking_status"] for b in status["bookings"]] == ["PENDING"]


def test_paid_webhook_confirms_bookings(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    assert api.webhook("checkout.session.completed", session_id).status_code == 200

    status = _status(customer, session_id)
    assert status["payment_status"] == "SUCCEEDED"
    assert [(b["booking_status"], b["payment_status"]) for b in status["bookings"]] == [
        ("CONFIRMED", "PAID")
    ]


def test_repeat_webhook_delivery_is_harmless(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    api.webhook("checkout.session.completed", session_id)
    # Stripe retries, and can deliver a late "expired" after completion.
    assert api.webhook("checkout.session.completed", session_id).status_code == 200
    assert api.webhook("checkout.session.expired", session_id).status_code == 200

    status = _status(customer, session_id)
    assert status["payment_status"] == "SUCCEEDED"
    assert status["bookings"][0]["booking_status"] == "CONFIRMED"


def test_unpaid_completion_waits_for_async_payment(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    api.webhook("checkout.session.completed", session_id, payment_status="unpaid")
    assert _status(customer, session_id)["payment_status"] == "PENDING"

    api.webhook("checkout.session.async_payment_succeeded", session_id)
    assert _status(customer, session_id)["payment_status"] == "SUCCEEDED"


def test_expired_checkout_frees_the_place(api: Api, customer, other_customer):
    data, day = _booked(api, customer, capacity=1)
    session_id = api.session_id(data["checkout_url"])

    # Full while the first checkout is open...
    their_child = api.new_child(other_customer)
    assert api.book(other_customer, {their_child["id"]: [day]}).status_code == 409

    api.webhook("checkout.session.expired", session_id)

    status = _status(customer, session_id)
    assert status["payment_status"] == "FAILED"
    assert status["bookings"][0]["booking_status"] == "EXPIRED"

    # ...and bookable once it expires.
    assert api.book(other_customer, {their_child["id"]: [day]}).status_code == 201


def test_resuming_returns_the_open_checkout(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()
    key = uuid.uuid4().hex

    first = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]
    again = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]

    assert again["checkout_url"] == first["checkout_url"]


def test_resuming_after_expiry_starts_a_new_checkout(api: Api, customer, fake_stripe):
    child = api.new_child(customer)
    day = api.service_day()
    key = uuid.uuid4().hex

    first = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]
    old_session = api.session_id(first["checkout_url"])

    # Stripe has expired the session, but its webhook hasn't arrived yet.
    fake_stripe.state.sessions[old_session].status = "expired"

    again = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]
    new_session = api.session_id(again["checkout_url"])
    assert new_session != old_session

    # The old session's late "expired" webhook must not cancel the bookings
    # the new checkout is about to pay for.
    api.webhook("checkout.session.expired", old_session)
    assert _status(customer, new_session)["bookings"][0]["booking_status"] == "PENDING"

    api.webhook("checkout.session.completed", new_session)
    assert _status(customer, new_session)["bookings"][0]["booking_status"] == "CONFIRMED"


def test_reusing_a_paid_bookings_key(api: Api, customer):
    key = uuid.uuid4().hex
    data, day = _booked(api, customer, key=key)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]}, idempotency_key=key)

    assert response.status_code == 409


def test_forged_webhook_is_rejected(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    response = api.webhook("checkout.session.completed", session_id, signature="invalid")

    assert response.status_code == 400
    assert _status(customer, session_id)["payment_status"] == "PENDING"


def test_checkout_status_is_private(api: Api, customer, other_customer):
    data, _ = _booked(api, customer)

    response = other_customer.client.get(
        f"/booking/v1/checkout/{api.session_id(data['checkout_url'])}"
    )

    assert response.status_code == 404


def test_unknown_checkout(customer):
    response = customer.client.get("/booking/v1/checkout/cs_test_unknown")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# The real StripeClient (the services get FakeStripe), network call stubbed
# ---------------------------------------------------------------------------

def test_stripe_gets_a_plain_currency_code():
    from app.db.models import CurrencyCodeEnum
    from app.integrations.payments.stripe.client import _currency_code

    # str() of the generated (str, Enum) classes is "CurrencyCodeEnum.AUD",
    # which Stripe rejects.
    assert _currency_code(CurrencyCodeEnum.AUD) == "aud"
    assert _currency_code("AUD") == "aud"


def test_stripe_failures_become_a_502(monkeypatch):
    import pytest
    import stripe

    from app.errors.payments import PaymentProviderError
    from app.integrations.payments.stripe.client import CheckoutLineItem, StripeClient

    def fail(**_):
        raise stripe.InvalidRequestError("Invalid currency", "currency")

    monkeypatch.setattr(stripe.checkout.Session, "create", fail)

    with pytest.raises(PaymentProviderError):
        StripeClient().create_checkout_session(
            line_items=[CheckoutLineItem(description="Test", amount_cents=100)],
            currency="AUD",
            metadata={},
            success_url="https://example.test/success",
            cancel_url="https://example.test/cancel",
            idempotency_key="test",
        )
