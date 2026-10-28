"""
Booking and refund references: a short code ("BK-7K3Q9P", "RF-…") the
database gives each booking group and refund. It's stored, shown on every
booking screen and the family's emails, searchable by staff, and on the
Stripe payment and refund, so a payment can be found on Stripe by what the
family quotes.
"""

import re

from app.integrations.email.messages import BookingConfirmationEmail, RefundConfirmationEmail
from tests.factories import Api


# No lookalikes: no 0/O or 1/I/L.
BOOKING_REFERENCE = re.compile(r"^BK-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{6}$")
REFUND_REFERENCE = re.compile(r"^RF-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{6}$")


def _booked(api: Api, customer) -> dict:
    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 201, response.text

    return response.json()["data"]


def _stored(api: Api, group_id: str) -> str:
    [(reference,)] = api.sql("SELECT reference FROM public.booking_groups WHERE id = :id", id=group_id)

    return reference


def _paid(api: Api, data: dict) -> None:
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))


# A new booking gets its own reference in the code's format, and two
# bookings never share one.
def test_each_booking_gets_a_reference(api: Api, customer):
    first = _stored(api, _booked(api, customer)["booking_group_id"])
    second = _stored(api, _booked(api, customer)["booking_group_id"])

    assert BOOKING_REFERENCE.match(first), first
    assert BOOKING_REFERENCE.match(second), second
    assert first != second


# The family sees the stored reference on the success page, the booking's
# review and My bookings.
def test_the_family_sees_it(api: Api, customer):
    data = _booked(api, customer)
    group_id = data["booking_group_id"]
    reference = _stored(api, group_id)

    status = customer.client.get(f"/booking/v1/checkout/{api.session_id(data['checkout_url'])}").json()["data"]
    group = customer.client.get(f"/booking/v1/groups/{group_id}").json()["data"]
    [summary] = [g for g in customer.client.get("/booking/v1/groups").json()["data"] if g["booking_group_id"] == group_id]

    assert status["reference"] == group["reference"] == summary["reference"] == reference


# The Stripe payment carries it: as its description (what the Stripe
# dashboard lists and searches) and in its metadata.
def test_stripe_payment_carries_it(api: Api, customer, fake_stripe):
    data = _booked(api, customer)
    reference = _stored(api, data["booking_group_id"])

    created = fake_stripe.state.created[-1]

    assert created["description"].startswith(f"Booking {reference} at ")
    assert created["metadata"]["reference"] == reference


# The confirmation email quotes the stored reference.
def test_confirmation_email_quotes_it(api: Api, customer, sent_emails):
    data = _booked(api, customer)
    _paid(api, data)

    [email] = sent_emails(BookingConfirmationEmail)

    assert email.reference == _stored(api, data["booking_group_id"])


# Staff find the family by the reference they quote, in any case, and see
# it against the payment on the family's page.
def test_staff_find_a_family_by_it(api: Api, admin, customer):
    data = _booked(api, customer)
    _paid(api, data)
    reference = _stored(api, data["booking_group_id"])
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    found = admin.get("/families/v1/", params={"q": reference.lower()}).json()["data"]
    assert [family["user_id"] for family in found] == [user_id]

    payments = admin.get(f"/families/v1/{user_id}/payments").json()["data"]
    assert reference in [payment["reference"] for payment in payments]


# A refund gets its own reference: on the refund email and the Stripe
# refund's metadata.
def test_refunds_get_a_reference(api: Api, customer, fake_stripe, sent_emails):
    data = _booked(api, customer)
    _paid(api, data)
    [line] = customer.client.get(f"/booking/v1/groups/{data['booking_group_id']}").json()["data"]["bookings"]

    response = customer.client.post("/refunds/v1/", json={"booking_id": line["id"]})
    assert response.status_code == 201, response.text

    [(reference,)] = api.sql("SELECT reference FROM public.refunds WHERE booking_id = :id", id=line["id"])
    assert REFUND_REFERENCE.match(reference), reference

    [(stripe_refund_id, stripe_refund)] = list(fake_stripe.state.refunds.items())
    assert stripe_refund["metadata"]["reference"] == reference

    api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded")

    [email] = sent_emails(RefundConfirmationEmail)
    assert email.reference == reference
