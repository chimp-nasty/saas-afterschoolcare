"""
Payments are confirmed even when Stripe's webhook doesn't arrive
(docs/payment-confirmation.md). Whenever we ask Stripe about a checkout
(the success page, cancelling, continuing to payment, the scheduled payment
check) and Stripe says it has finished, it's settled on the spot through the
same path as the webhook. Settling is safe to repeat, so whichever comes
first wins and the rest change nothing. Checkout is refused while the
webhook secrets aren't set up.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.email.messages import BookingConfirmationEmail
from app.main import app
from tests.factories import Api


SECRET = "test-payment-check-secret"


@pytest.fixture(autouse=True)
def payment_check_secret(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_CHECK_SECRET", SECRET)


def _booked(api: Api, customer) -> tuple[dict, str]:
    """Book one new day for a new child; returns (response json data, session id)."""
    child = api.new_child(customer)

    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 201, response.text

    data = response.json()["data"]

    return data, api.session_id(data["checkout_url"])


def _state(api: Api, group_id: str) -> tuple[str, list[tuple[str, str]]]:
    """
    The group's latest payment attempt and its bookings, read straight from
    the database (the success page would settle the payment by looking).
    """
    [(attempt_status,)] = api.sql(
        """
        SELECT stripe_status::text FROM public.payment_attempts
        WHERE booking_group_id = :id
        ORDER BY created_at DESC
        LIMIT 1
        """,
        id=group_id,
    )

    bookings = api.sql(
        "SELECT booking_status::text, payment_status::text FROM public.bookings WHERE booking_group_id = :id",
        id=group_id,
    )

    return attempt_status, [tuple(row) for row in bookings]


def _success_page(customer, session_id: str) -> dict:
    response = customer.client.get(f"/booking/v1/checkout/{session_id}")
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _payment_check(*, secret: str | None = SECRET):
    """The scheduled payment check, as Cloud Scheduler calls it (no Origin)."""
    client = TestClient(app, base_url=f"https://{settings.BASE_DOMAIN}/api")
    headers = {"X-Payment-Check-Secret": secret} if secret else {}

    return client.post("/internal/v1/payment-check", headers=headers)


# ---------------------------------------------------------------------------
# The success page
# ---------------------------------------------------------------------------

# The family pays and lands on the success page, but the webhook never
# arrives: the page asks Stripe, sees the payment, and confirms the booking,
# with a receipt and one confirmation email.
def test_success_page_confirms_a_payment_the_webhook_missed(api: Api, customer, sent_emails):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    status = _success_page(customer, session_id)

    assert status["payment_status"] == "SUCCEEDED"
    assert [(b["booking_status"], b["payment_status"]) for b in status["bookings"]] == [
        ("CONFIRMED", "PAID")
    ]

    group = customer.client.get(f"/booking/v1/groups/{data['booking_group_id']}").json()["data"]
    assert group["paid_at"] is not None
    assert group["receipt_url"].startswith("https://pay.stripe.test/receipts/pi_test_")

    [email] = sent_emails(BookingConfirmationEmail)
    assert email.to_email == customer.email


# The webhook turns up after the success page already confirmed the
# payment: nothing changes and no second email goes out. Reloading the
# success page doesn't either.
def test_late_webhook_after_the_success_page_is_harmless(api: Api, customer, sent_emails):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    _success_page(customer, session_id)
    _success_page(customer, session_id)
    assert api.webhook("checkout.session.completed", session_id).status_code == 200

    assert _state(api, data["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])
    assert len(sent_emails(BookingConfirmationEmail)) == 1


# Opening the success page before paying (or while Stripe is still
# processing) changes nothing: the checkout stays open and pending.
def test_success_page_leaves_an_unpaid_checkout_pending(api: Api, customer, fake_stripe):
    data, session_id = _booked(api, customer)

    assert _success_page(customer, session_id)["payment_status"] == "PENDING"
    assert fake_stripe.state.sessions[session_id].status == "open"
    assert _state(api, data["booking_group_id"]) == ("PENDING", [("PENDING", "PENDING")])


# A slower payment method (e.g. bank debit) completes the checkout before
# the money arrives: the success page keeps it pending, as the webhook does.
def test_success_page_waits_for_a_delayed_payment(api: Api, customer):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id, payment_status="unpaid")

    assert _success_page(customer, session_id)["payment_status"] == "PENDING"
    assert _state(api, data["booking_group_id"]) == ("PENDING", [("PENDING", "PENDING")])


# If Stripe can't be reached, the success page still shows what we know
# (pending) instead of failing.
def test_success_page_works_while_stripe_is_down(api: Api, customer, fake_stripe, monkeypatch):
    from app.errors.payments import PaymentProviderError

    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    def stripe_down(_self, **_):
        raise PaymentProviderError(log_reason="Stripe unavailable")

    monkeypatch.setattr(fake_stripe, "get_checkout_session", stripe_down)

    assert _success_page(customer, session_id)["payment_status"] == "PENDING"


# ---------------------------------------------------------------------------
# Cancelling and continuing to payment
# ---------------------------------------------------------------------------

# Cancelling a booking that was paid on Stripe (webhook missed) confirms the
# payment instead of leaving it stuck: the family is told it's paid, and the
# booking now shows as confirmed and paid.
def test_cancelling_a_paid_checkout_confirms_it(api: Api, customer, sent_emails):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    response = customer.client.post(f"/booking/v1/groups/{data['booking_group_id']}/cancel")

    assert response.status_code == 400
    assert response.json()["msg"] == "Booking group is already marked as paid"
    assert _state(api, data["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])
    assert len(sent_emails(BookingConfirmationEmail)) == 1


# "Continue to payment" on a booking that was already paid on Stripe
# (webhook missed) never opens a second checkout, so the family can't be
# charged twice; the payment is confirmed instead.
def test_continuing_to_payment_never_charges_twice(api: Api, customer, fake_stripe):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)
    checkouts = len(fake_stripe.state.created)

    response = customer.client.post(f"/booking/v1/groups/{data['booking_group_id']}/checkout")

    assert response.status_code == 400
    assert response.json()["msg"] == "Booking group is already marked as paid"
    assert len(fake_stripe.state.created) == checkouts
    assert _state(api, data["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])


# Sending the same booking again (same idempotency key, e.g. the Book
# button pressed again) after paying on Stripe doesn't open a second
# checkout either.
def test_resending_a_paid_booking_never_charges_twice(api: Api, customer, fake_stripe):
    child = api.new_child(customer)
    day = api.service_day()
    key = uuid.uuid4().hex

    first = api.book(customer, {child["id"]: [day]}, idempotency_key=key).json()["data"]
    api.pay_at_stripe(api.session_id(first["checkout_url"]))
    checkouts = len(fake_stripe.state.created)

    response = api.book(customer, {child["id"]: [day]}, idempotency_key=key)

    assert response.status_code == 400
    assert len(fake_stripe.state.created) == checkouts
    assert _state(api, first["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])


# A delayed payment that's still processing on Stripe can't be paid again
# or cancelled: the family is told it's processing, and nothing changes.
def test_a_processing_payment_cant_be_paid_again_or_cancelled(api: Api, customer, fake_stripe):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id, payment_status="unpaid")
    checkouts = len(fake_stripe.state.created)
    group = data["booking_group_id"]

    for path in (f"/booking/v1/groups/{group}/checkout", f"/booking/v1/groups/{group}/cancel"):
        response = customer.client.post(path)

        assert response.status_code == 409, path
        assert response.json()["msg"] == "Your payment is still processing. We'll email you once it goes through."

    assert len(fake_stripe.state.created) == checkouts
    assert _state(api, group) == ("PENDING", [("PENDING", "PENDING")])


# ---------------------------------------------------------------------------
# The scheduled payment check
# ---------------------------------------------------------------------------

# The family paid and closed the tab before the success page, and the
# webhook never came: the scheduled check asks Stripe and confirms it.
def test_payment_check_confirms_a_missed_payment(api: Api, customer, sent_emails):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    response = _payment_check()

    assert response.status_code == 200, response.text
    assert _state(api, data["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])
    assert len(sent_emails(BookingConfirmationEmail)) == 1


# A checkout Stripe expired (webhook missed) is released by the check, so
# its place goes back; one still open is left alone.
def test_payment_check_releases_expired_checkouts_only(api: Api, customer, other_customer):
    expired, expired_session = _booked(api, customer)
    still_open, _ = _booked(api, other_customer)
    api.expire_at_stripe(expired_session)

    assert _payment_check().status_code == 200

    assert _state(api, expired["booking_group_id"]) == ("FAILED", [("EXPIRED", "FAILED")])
    assert _state(api, still_open["booking_group_id"]) == ("PENDING", [("PENDING", "PENDING")])


# A payment Stripe can't tell us about (it errors for that session) doesn't
# stop the check settling the others; it's tried again next time.
def test_payment_check_carries_on_past_a_failure(api: Api, customer, other_customer, fake_stripe):
    unknown, unknown_session = _booked(api, customer)
    paid, paid_session = _booked(api, other_customer)
    api.pay_at_stripe(paid_session)
    del fake_stripe.state.sessions[unknown_session]

    assert _payment_check().status_code == 200

    assert _state(api, unknown["booking_group_id"]) == ("PENDING", [("PENDING", "PENDING")])
    assert _state(api, paid["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])


# Running the check again, or the webhook arriving afterwards, changes
# nothing and sends no second email.
def test_payment_check_is_safe_to_repeat(api: Api, customer, sent_emails):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    _payment_check()
    _payment_check()
    api.webhook("checkout.session.completed", session_id)

    assert _state(api, data["booking_group_id"]) == ("SUCCEEDED", [("CONFIRMED", "PAID")])
    assert len(sent_emails(BookingConfirmationEmail)) == 1


# Only Cloud Scheduler, with the secret, can run the check: no secret or the
# wrong one is refused (404, as if it weren't there), and nothing is settled.
@pytest.mark.parametrize("secret", [None, "wrong-secret"])
def test_payment_check_needs_the_secret(api: Api, customer, secret):
    data, session_id = _booked(api, customer)
    api.pay_at_stripe(session_id)

    assert _payment_check(secret=secret).status_code == 404
    assert _state(api, data["booking_group_id"]) == ("PENDING", [("PENDING", "PENDING")])


# With no secret configured, the check can't be run at all (404), even by
# sending an empty one.
def test_payment_check_is_off_without_a_configured_secret(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_CHECK_SECRET", None)

    assert _payment_check(secret="").status_code == 404


# ---------------------------------------------------------------------------
# Refusing checkout while payments can't be confirmed
# ---------------------------------------------------------------------------

# While the webhook secrets are missing or still the deploy runbook's
# "unset" placeholder, booking is refused before the family is sent to
# Stripe (503), no checkout is opened and no place is held. Once they're
# set, the same booking goes through.
@pytest.mark.parametrize("placeholder", ["", "unset"])
def test_checkout_is_refused_until_webhooks_are_set_up(
    api: Api, customer, fake_stripe, monkeypatch, placeholder
):
    child = api.new_child(customer)
    day = api.service_day(capacity=1)
    real = (settings.STRIPE_WEBHOOK_SECRET, settings.STRIPE_CONNECT_WEBHOOK_SECRET)

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", placeholder)
    monkeypatch.setattr(settings, "STRIPE_CONNECT_WEBHOOK_SECRET", placeholder)

    response = api.book(customer, {child["id"]: [day]})

    assert response.status_code == 503
    assert response.json()["msg"] == "Payments aren't available right now. Please try again later."
    assert fake_stripe.state.created == []

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", real[0])
    monkeypatch.setattr(settings, "STRIPE_CONNECT_WEBHOOK_SECRET", real[1])

    assert api.book(customer, {child["id"]: [day]}).status_code == 201
