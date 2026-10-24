"""
Stripe checkout: creating a booking opens a checkout session, and only the
webhook moves payment state (see tests.factories.FakeStripe).
"""

import uuid

from app.core.config import settings
from app.integrations.email.messages import BookingConfirmationEmail
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


# Booking opens a Stripe checkout for the right amount, with success and
# cancel links pointing back to this tenant's site and location.
def test_booking_opens_a_checkout(api: Api, customer, fake_stripe):
    data, _ = _booked(api, customer)

    assert data["checkout_url"].startswith("https://checkout.stripe.test/")

    created = fake_stripe.state.created[-1]
    site = f"https://tenant1.{settings.BASE_DOMAIN}/location1"
    assert created["success_url"] == f"{site}/bookings/success?session_id={{CHECKOUT_SESSION_ID}}"
    assert created["cancel_url"] == f"{site}/bookings/new"
    assert [item.amount_cents for item in created["line_items"]] == [data["amount"]]


# A booking request sent from another website is refused (403) before it
# reaches the booking code, so Stripe can't be told to send customers back
# to a site that isn't ours.
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

    assert response.status_code == 403
    assert response.json()["msg"] == "This request didn't come from this site."


# Straight after booking, the payment and the booking are both PENDING, for
# the full amount.
def test_new_checkout_is_pending(api: Api, customer):
    data, _ = _booked(api, customer)

    status = _status(customer, api.session_id(data["checkout_url"]))

    assert status["payment_status"] == "PENDING"
    assert status["total_cents"] == data["amount"]
    assert [b["booking_status"] for b in status["bookings"]] == ["PENDING"]


# When Stripe's 'paid' webhook arrives, the payment SUCCEEDS and the
# bookings become CONFIRMED and PAID.
def test_paid_webhook_confirms_bookings(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    assert api.webhook("checkout.session.completed", session_id).status_code == 200

    status = _status(customer, session_id)
    assert status["payment_status"] == "SUCCEEDED"
    assert [(b["booking_status"], b["payment_status"]) for b in status["bookings"]] == [
        ("CONFIRMED", "PAID")
    ]


# paid_at is empty until the payment goes through, then the paid webhook
# sets it, and the review page and 'My bookings' list show the same time.
def test_paid_webhook_records_when_it_was_paid(api: Api, customer):
    data, _ = _booked(api, customer)
    group_id = data["booking_group_id"]

    def paid_at() -> tuple:
        group = customer.client.get(f"/booking/v1/groups/{group_id}").json()["data"]
        [summary] = [
            g for g in customer.client.get("/booking/v1/groups").json()["data"]
            if g["booking_group_id"] == group_id
        ]
        return group["paid_at"], summary["paid_at"]

    assert paid_at() == (None, None)

    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    group_paid_at, summary_paid_at = paid_at()
    assert group_paid_at is not None
    assert summary_paid_at == group_paid_at


# When the payment goes through, the booking keeps a link to Stripe's receipt
# for it, which the review page shows as "View receipt".
def test_paid_webhook_records_the_receipt(api: Api, customer):
    data, _ = _booked(api, customer)

    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    group = customer.client.get(f"/booking/v1/groups/{data['booking_group_id']}").json()["data"]
    assert group["receipt_url"].startswith("https://pay.stripe.test/receipts/pi_test_")


# If Stripe can't give the receipt link at that moment, the payment still
# settles: the booking is confirmed, just without a receipt link.
def test_payment_settles_without_a_receipt(api: Api, customer, fake_stripe, monkeypatch):
    from app.errors.payments import PaymentProviderError

    def receipts_down(_self, **_):
        raise PaymentProviderError(log_reason="Stripe unavailable")

    monkeypatch.setattr(fake_stripe, "get_receipt_url", receipts_down)

    data, _ = _booked(api, customer)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    group = customer.client.get(f"/booking/v1/groups/{data['booking_group_id']}").json()["data"]
    assert group["status"] == "CONFIRMED"
    assert group["receipt_url"] is None


# A checkout that expires without payment never gets a paid_at.
def test_expired_checkout_is_never_paid(api: Api, customer):
    data, _ = _booked(api, customer)

    api.webhook("checkout.session.expired", api.session_id(data["checkout_url"]))

    group = customer.client.get(f"/booking/v1/groups/{data['booking_group_id']}").json()["data"]
    assert group["paid_at"] is None


# Stripe can resend webhooks or send a late 'expired' after payment; none of
# these undo a confirmed payment.
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


# For slower payment methods (e.g. bank debit), a completed but unpaid
# checkout stays PENDING until Stripe says the payment succeeded.
def test_unpaid_completion_waits_for_async_payment(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    api.webhook("checkout.session.completed", session_id, payment_status="unpaid")
    assert _status(customer, session_id)["payment_status"] == "PENDING"

    api.webhook("checkout.session.async_payment_succeeded", session_id)
    assert _status(customer, session_id)["payment_status"] == "SUCCEEDED"


# While a checkout is open it holds the place (others get 409). When it
# expires, the booking becomes EXPIRED and the place can be booked by
# someone else.
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


# Retrying a booking with the same idempotency key returns the same open
# Stripe checkout link.
def test_resuming_returns_the_open_checkout(api: Api, customer):
    child = api.new_child(customer)
    day = api.service_day()
    key = uuid.uuid4().hex

    first = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]
    again = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]

    assert again["checkout_url"] == first["checkout_url"]


# If the old checkout expired on Stripe, retrying opens a new one. The old
# checkout's late 'expired' webhook must not cancel the bookings the new one
# is paying for.
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


# An idempotency key that already belongs to a paid booking can't be reused
# for a different booking (409).
def test_reusing_a_paid_bookings_key(api: Api, customer):
    key = uuid.uuid4().hex
    data, day = _booked(api, customer, key=key)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]}, idempotency_key=key)

    assert response.status_code == 409


# A webhook with an invalid Stripe signature is rejected (400) and the
# payment stays PENDING.
def test_forged_webhook_is_rejected(api: Api, customer):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    response = api.webhook("checkout.session.completed", session_id, signature="invalid")

    assert response.status_code == 400
    assert _status(customer, session_id)["payment_status"] == "PENDING"


# A customer can't look up another customer's checkout status (404).
def test_checkout_status_is_private(api: Api, customer, other_customer):
    data, _ = _booked(api, customer)

    response = other_customer.client.get(
        f"/booking/v1/checkout/{api.session_id(data['checkout_url'])}"
    )

    assert response.status_code == 404


# Looking up a checkout session that doesn't exist returns 404.
def test_unknown_checkout(customer):
    response = customer.client.get("/booking/v1/checkout/cs_test_unknown")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# The real StripeClient (the services get FakeStripe), network call stubbed
# ---------------------------------------------------------------------------

# Currency codes are sent to Stripe as plain lowercase text ('aud'), whether
# they start as our enum or as a string.
def test_stripe_gets_a_plain_currency_code():
    from app.db.models import CurrencyCodeEnum
    from app.integrations.payments.stripe.client import _currency_code

    # str() of the generated (str, Enum) classes is "CurrencyCodeEnum.AUD",
    # which Stripe rejects.
    assert _currency_code(CurrencyCodeEnum.AUD) == "aud"
    assert _currency_code("AUD") == "aud"


# An error from Stripe while creating a checkout is turned into our
# PaymentProviderError instead of leaking Stripe's own exception, and a
# booking that hits it gets a 502 with a retry message.
def test_stripe_failures_become_a_502(api: Api, customer, fake_stripe, monkeypatch):
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

    # The services use FakeStripe; make it fail the same way.
    def provider_down(self, **_):
        raise PaymentProviderError()

    monkeypatch.setattr(fake_stripe, "create_checkout_session", provider_down)

    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]})

    assert response.status_code == 502
    assert response.json()["msg"] == "Payment provider error. Please try again."


# A paid booking emails the family one confirmation (even when Stripe
# repeats the event), with the total and a reference, and nothing about the
# children or the days.
def test_paid_booking_emails_a_confirmation(api: Api, customer, sent_emails):
    data, _ = _booked(api, customer)
    session_id = api.session_id(data["checkout_url"])

    api.webhook("checkout.session.completed", session_id)
    api.webhook("checkout.session.completed", session_id)

    [email] = sent_emails(BookingConfirmationEmail)
    assert email.to_email == customer.email
    assert email.total_cents == data["amount"]
    assert email.reference.startswith("BK-")


# A checkout that expires unpaid sends no confirmation.
def test_expired_checkout_sends_no_confirmation(api: Api, customer, sent_emails):
    data, _ = _booked(api, customer)

    api.webhook("checkout.session.expired", api.session_id(data["checkout_url"]))

    assert sent_emails(BookingConfirmationEmail) == []
