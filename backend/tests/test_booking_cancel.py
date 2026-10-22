"""
Cancelling a paid booking without a refund, and reinstating it. Once the
family's refund window has closed (refund_cutoff_days before the day, 2 in
the dev seed), until the session starts, the family (or an admin for them,
under the same rules) can cancel a booking: its place goes back and it
stays paid. Until the session starts it can be put back, if there's still
a place and the booking rules pass. Before the cutoff it's a refund
instead; once the session has started nothing changes.
"""

from tests.factories import Api


def _ids(api: Api, booking_id: str) -> tuple[str, str]:
    """The booking's group and service day."""
    [(group_id, day_id)] = api.sql(
        "SELECT booking_group_id::text, location_service_day_id::text FROM public.bookings WHERE id = :id",
        id=booking_id,
    )

    return group_id, day_id


def _status(api: Api, booking_id: str) -> tuple[str, str, bool]:
    [(booking_status, payment_status, cancelled)] = api.sql(
        "SELECT booking_status::text, payment_status::text, cancelled_at IS NOT NULL FROM public.bookings WHERE id = :id",
        id=booking_id,
    )

    return booking_status, payment_status, cancelled


def _line(customer, api: Api, booking_id: str) -> dict:
    group_id, _ = _ids(api, booking_id)
    group = customer.client.get(f"/booking/v1/groups/{group_id}").json()["data"]

    return next(line for line in group["bookings"] if line["id"] == booking_id)


# Tomorrow's booking is past the refund cutoff: the family cancels it, it
# stays paid, then they put it back.
def test_cancel_and_reinstate(api: Api, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)

    line = _line(customer, api, booking_id)
    assert (line["is_refundable"], line["is_cancellable"], line["is_reinstatable"]) == (False, True, False)

    response = customer.client.post(f"/booking/v1/{booking_id}/cancel")
    assert response.status_code == 200, response.text
    assert _status(api, booking_id) == ("CANCELLED", "PAID", True)
    assert _line(customer, api, booking_id)["is_reinstatable"] is True

    response = customer.client.post(f"/booking/v1/{booking_id}/reinstate")
    assert response.status_code == 200, response.text
    assert _status(api, booking_id) == ("CONFIRMED", "PAID", False)


# Inside the refund window it's a refund, not a cancel.
def test_cannot_cancel_before_the_cutoff(api: Api, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=10)

    assert _line(customer, api, booking_id)["is_cancellable"] is False
    assert customer.client.post(f"/booking/v1/{booking_id}/cancel").status_code == 409
    assert _status(api, booking_id)[0] == "CONFIRMED"


# Once the session has started (here, a past day) nothing changes.
def test_cannot_cancel_after_the_session_started(api: Api, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=-1)

    assert customer.client.post(f"/booking/v1/{booking_id}/cancel").status_code == 409


# A cancelled booking can't be put back once its place has gone; the day's
# capacity is put back afterwards.
def test_reinstate_needs_a_place(api: Api, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)
    _, day_id = _ids(api, booking_id)
    customer.client.post(f"/booking/v1/{booking_id}/cancel")

    [(capacity,)] = api.sql("SELECT capacity FROM public.location_service_days WHERE id = :id", id=day_id)
    api.sql(
        "UPDATE public.location_service_days SET capacity = ("
        "  SELECT count(*) FROM public.bookings b WHERE b.location_service_day_id = :id"
        "  AND b.booking_status IN ('PENDING', 'CONFIRMED')"
        ") WHERE id = :id",
        id=day_id,
    )

    try:
        response = customer.client.post(f"/booking/v1/{booking_id}/reinstate")
        assert response.status_code == 409
        assert response.json()["msg"] == "No capacity available for one or more of the selected days"
        assert _status(api, booking_id)[0] == "CANCELLED"
    finally:
        api.sql("UPDATE public.location_service_days SET capacity = :c WHERE id = :id", c=capacity, id=day_id)


# A booking that was refunded, or one never paid, can't be reinstated.
def test_only_paid_cancellations_reinstate(api: Api, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)
    api.sql(
        "UPDATE public.bookings SET booking_status = 'CANCELLED', payment_status = 'REFUNDED', cancelled_at = now() "
        "WHERE id = :id",
        id=booking_id,
    )

    assert customer.client.post(f"/booking/v1/{booking_id}/reinstate").status_code == 409


# An admin can cancel and reinstate a family's booking under the same
# rules; staff on the website and other families can't.
def test_who_can_cancel(api: Api, admin, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)
    other = api.new_customer()
    staff = api.new_staff(pin=None)

    assert other.client.post(f"/booking/v1/{booking_id}/cancel").status_code == 404
    assert staff.client.post(f"/booking/v1/{booking_id}/cancel").status_code == 403

    assert admin.post(f"/booking/v1/{booking_id}/cancel").status_code == 200
    assert admin.post(f"/booking/v1/{booking_id}/reinstate").status_code == 200

    early = api.booking_on(customer, child["id"], days_from_today=10)
    assert admin.post(f"/booking/v1/{early}/cancel").status_code == 409


# The admin family page says what can be done with each booking.
def test_family_page_flags(api: Api, admin, customer):
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    bookings = admin.get(f"/families/v1/{user_id}/bookings").json()["data"]
    [listed] = [b for b in bookings if b["id"] == booking_id]
    assert (listed["is_cancellable"], listed["is_reinstatable"]) == (True, False)
