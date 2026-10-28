"""
Deactivating an account (docs/account-deactivation.md). A family deactivates
their account at a centre, after re-entering their password, once they have
no upcoming bookings. Nothing is deleted: the database stamps when, and a
keep-until date (stubbed as 7 years). While deactivated, the API refuses
every request at that centre except reading their account and asking to
reactivate, and RLS hides their own rows there too. An admin reactivates
them.
"""

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from tests.factories import Api


DEACTIVATED = "This account is deactivated."


def _user_id(api: Api, customer) -> str:
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    return user_id


def _location_id(api: Api) -> str:
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )

    return location_id


def _deactivate(customer, *, password: str | None = None):
    return customer.client.post("/account/v1/deactivate", json={"password": password or customer.password})


def _deactivated(api: Api, customer) -> list[tuple]:
    return api.sql(
        """
        SELECT deactivated_at, retain_until, reactivation_requested_at
        FROM public.family_deactivations
        WHERE user_id = :u AND location_id = :l
        """,
        u=_user_id(api, customer),
        l=_location_id(api),
    )


def _paid_future_booking(api: Api, customer) -> None:
    child = api.new_child(customer)
    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 201, response.text
    api.webhook("checkout.session.completed", api.session_id(response.json()["data"]["checkout_url"]))


# ---------------------------------------------------------------------------
# Deactivating
# ---------------------------------------------------------------------------

# With no upcoming bookings, the family deactivates after re-entering their
# password. The database stamps when, and keeps their records for 7 years
# from then (the stub until the retention work sets each record's date).
def test_family_deactivates_their_account(api: Api, customer):
    response = _deactivate(customer)

    assert response.status_code == 200, response.text

    [(deactivated_at, retain_until, requested_at)] = _deactivated(api, customer)
    assert retain_until.date() == deactivated_at.date().replace(year=deactivated_at.year + 7)
    assert requested_at is None


# The wrong password is refused and nothing changes.
def test_deactivating_needs_the_password(api: Api, customer):
    response = _deactivate(customer, password="not-the-password")

    assert response.status_code == 400
    assert response.json()["msg"] == "Your current password isn't right."
    assert _deactivated(api, customer) == []


# A family with an upcoming paid booking can't deactivate until they've
# cancelled or refunded it (409, saying why).
def test_upcoming_bookings_block_deactivating(api: Api, customer):
    _paid_future_booking(api, customer)

    response = _deactivate(customer)

    assert response.status_code == 409
    assert response.json()["msg"] == "Cancel or refund your upcoming bookings before deactivating your account."
    assert _deactivated(api, customer) == []


# A booking still awaiting payment counts as upcoming too.
def test_a_pending_booking_blocks_deactivating(api: Api, customer):
    child = api.new_child(customer)
    assert api.book(customer, {child["id"]: [api.service_day()]}).status_code == 201

    assert _deactivate(customer).status_code == 409


# Past bookings don't stop a family deactivating.
def test_past_bookings_dont_block_deactivating(api: Api, customer):
    child = api.new_child(customer)
    api.booking_on(customer, child["id"], days_from_today=-1)

    assert _deactivate(customer).status_code == 200


# Only family accounts can be deactivated: an admin's own login is refused
# (403), so nobody locks a centre out of its own staff.
def test_staff_cant_deactivate(admin):
    response = admin.post("/account/v1/deactivate", json={"password": "123"})

    assert response.status_code == 403
    assert response.json()["msg"] == "Only family accounts can be deactivated."


# ---------------------------------------------------------------------------
# While deactivated
# ---------------------------------------------------------------------------

# Once deactivated, the API refuses the family's requests at the centre
# (403, the same message everywhere), whatever the endpoint, even with the
# login they already had open.
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/children/v1/"),
        ("get", "/customer/v1/profile"),
        ("get", "/booking/v1/groups"),
        ("get", "/pickups/v1/"),
        ("get", "/action/v1/"),
        ("post", "/booking/v1/"),
    ],
)
def test_the_api_refuses_a_deactivated_family(api: Api, customer, method, path):
    assert _deactivate(customer).status_code == 200

    response = getattr(customer.client, method)(path, **({"json": {}} if method == "post" else {}))

    assert response.status_code == 403
    assert response.json()["msg"] == DEACTIVATED


# They can still see who they are (session and account), ask to be
# reactivated, and log out.
def test_a_deactivated_family_can_still_log_out_and_ask(api: Api, customer):
    assert _deactivate(customer).status_code == 200

    assert customer.client.get("/auth/v1/session").status_code == 200
    assert customer.client.get("/account/v1/").status_code == 200
    assert customer.client.post("/account/v1/reactivation-request").status_code == 200
    assert customer.client.post("/auth/v1/logout").status_code == 200


# The session tells the website the family is deactivated (so it shows only
# the deactivated page) and whether they've asked to come back.
def test_the_session_says_so(api: Api, customer):
    def session() -> dict:
        return customer.client.get("/auth/v1/session").json()["data"]

    assert (session()["is_deactivated"], session()["reactivation_requested"]) == (False, False)

    assert _deactivate(customer).status_code == 200
    assert (session()["is_deactivated"], session()["reactivation_requested"]) == (True, False)

    customer.client.post("/account/v1/reactivation-request")
    assert (session()["is_deactivated"], session()["reactivation_requested"]) == (True, True)


# Logging in again works (so they can see why and ask), but the API still
# refuses everything else.
def test_logging_in_again_is_still_refused(api: Api, customer):
    assert _deactivate(customer).status_code == 200

    again = api.login(customer.email, customer.password)

    assert again.get("/children/v1/").status_code == 403


# The database refuses too, whatever the API does: acting as the family at
# the centre, RLS shows none of their own rows.
def test_rls_hides_a_deactivated_familys_rows(api: Api, customer):
    api.new_child(customer)
    user_id = _user_id(api, customer)
    location_id = _location_id(api)

    def own_children() -> int:
        with SessionLocal() as db:
            db.execute(
                text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
                {"u": user_id, "l": location_id},
            )

            return db.execute(text("SELECT count(*) FROM public.child_profile WHERE user_id = :u"), {"u": user_id}).scalar_one()

    assert own_children() == 1

    assert _deactivate(customer).status_code == 200

    assert own_children() == 0


# The centre's admins still see the deactivated family's records.
def test_admins_still_see_a_deactivated_family(api: Api, admin, customer):
    api.new_child(customer, first_name="Persephone")
    assert _deactivate(customer).status_code == 200

    family = admin.get(f"/families/v1/{_user_id(api, customer)}")

    assert family.status_code == 200, family.text
    assert [child["first_name"] for child in family.json()["data"]["children"]] == ["Persephone"]
    assert family.json()["data"]["deactivated_at"] is not None


# ---------------------------------------------------------------------------
# Reactivating
# ---------------------------------------------------------------------------

# The family asks to be reactivated: the request is recorded (asking again
# changes nothing) and the centre's admins see it, on the family's page and
# in the list of requests.
def test_asking_to_reactivate(api: Api, admin, customer):
    assert _deactivate(customer).status_code == 200

    assert customer.client.post("/account/v1/reactivation-request").status_code == 200
    [(_, _, first_asked)] = _deactivated(api, customer)
    assert first_asked is not None

    assert customer.client.post("/account/v1/reactivation-request").status_code == 200
    [(_, _, asked_again)] = _deactivated(api, customer)
    assert asked_again == first_asked

    user_id = _user_id(api, customer)
    family = admin.get(f"/families/v1/{user_id}").json()["data"]
    assert family["reactivation_requested_at"] is not None

    requests = admin.get("/families/v1/reactivation-requests")
    assert requests.status_code == 200, requests.text
    assert user_id in [row["user_id"] for row in requests.json()["data"]]


# Asking to reactivate an account that isn't deactivated is a 409.
def test_asking_without_being_deactivated(customer):
    assert customer.client.post("/account/v1/reactivation-request").status_code == 409


# An admin reactivates the family: the deactivation is gone, they drop off
# the list of requests, and the family's login works again.
def test_admin_reactivates(api: Api, admin, customer):
    assert _deactivate(customer).status_code == 200
    customer.client.post("/account/v1/reactivation-request")
    user_id = _user_id(api, customer)

    response = admin.post(f"/families/v1/{user_id}/reactivate")

    assert response.status_code == 200, response.text
    assert _deactivated(api, customer) == []
    assert user_id not in [row["user_id"] for row in admin.get("/families/v1/reactivation-requests").json()["data"]]
    assert customer.client.get("/children/v1/").status_code == 200


# Reactivating a family that isn't deactivated is a 409.
def test_reactivating_an_active_family(api: Api, admin, customer):
    assert admin.post(f"/families/v1/{_user_id(api, customer)}/reactivate").status_code == 409


# A family can't reactivate themselves (families u is the centre's), and
# another business's admin can't find them (404).
def test_only_the_centres_admins_reactivate(api: Api, customer, tenant2_admin):
    assert _deactivate(customer).status_code == 200
    user_id = _user_id(api, customer)

    assert customer.client.post(f"/families/v1/{user_id}/reactivate").status_code == 403
    assert tenant2_admin.post(f"/families/v1/{user_id}/reactivate").status_code == 404
    assert _deactivated(api, customer) != []


# ---------------------------------------------------------------------------
# Bookings cancelled without a refund
# ---------------------------------------------------------------------------

def _cancelled_tomorrow(api: Api, customer) -> str:
    """A paid booking for tomorrow (past the refund cutoff), cancelled by the family: CANCELLED and still PAID."""
    child = api.new_child(customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)

    response = customer.client.post(f"/booking/v1/{booking_id}/cancel")
    assert response.status_code == 200, response.text

    return booking_id


def _status(api: Api, booking_id: str) -> tuple[str, str]:
    [(booking_status, payment_status)] = api.sql(
        "SELECT booking_status::text, payment_status::text FROM public.bookings WHERE id = :id",
        id=booking_id,
    )

    return booking_status, payment_status


# A cancelled-but-paid booking doesn't stop a family deactivating (it's not
# on the run sheet), but once they have, nobody can put it back, not even
# an admin, and the admin's page doesn't offer it.
def test_nobody_puts_back_a_deactivated_familys_booking(api: Api, admin, customer):
    booking_id = _cancelled_tomorrow(api, customer)
    assert _deactivate(customer).status_code == 200

    listed = admin.get(f"/families/v1/{_user_id(api, customer)}/bookings").json()["data"]
    assert [b["is_reinstatable"] for b in listed if b["id"] == booking_id] == [False]

    assert admin.post(f"/booking/v1/{booking_id}/reinstate").status_code != 200
    assert _status(api, booking_id) == ("CANCELLED", "PAID")


# An admin can refund a booking the family cancelled without a refund (any
# family, e.g. as a goodwill gesture). Once Stripe confirms, it's REFUNDED,
# keeping when it was cancelled, and it doesn't come back to the run sheet.
def test_admin_refunds_a_cancelled_booking(api: Api, admin, customer, fake_stripe):
    booking_id = _cancelled_tomorrow(api, customer)
    [(cancelled_at,)] = api.sql("SELECT cancelled_at FROM public.bookings WHERE id = :id", id=booking_id)

    response = admin.post("/refunds/v1/", json={"booking_id": booking_id})
    assert response.status_code in (200, 201), response.text

    [stripe_refund_id] = list(fake_stripe.state.refunds)
    assert api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded").status_code == 200

    assert _status(api, booking_id) == ("CANCELLED", "REFUNDED")
    assert api.sql("SELECT cancelled_at FROM public.bookings WHERE id = :id", id=booking_id) == [(cancelled_at,)]


# The family can't refund a booking they cancelled after the cutoff.
def test_family_cant_refund_a_cancelled_booking(api: Api, customer):
    booking_id = _cancelled_tomorrow(api, customer)

    assert customer.client.post("/refunds/v1/", json={"booking_id": booking_id}).status_code != 200
    assert _status(api, booking_id) == ("CANCELLED", "PAID")


# A refund for a family who has deactivated still goes through: Stripe's
# webhook acts as the family, and still reaches their booking and refund.
def test_a_deactivated_familys_refund_settles(api: Api, admin, customer, fake_stripe):
    booking_id = _cancelled_tomorrow(api, customer)
    assert _deactivate(customer).status_code == 200

    assert admin.post("/refunds/v1/", json={"booking_id": booking_id}).status_code in (200, 201)

    [stripe_refund_id] = list(fake_stripe.state.refunds)
    assert api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded").status_code == 200

    assert _status(api, booking_id) == ("CANCELLED", "REFUNDED")
    [(refund_status,)] = api.sql("SELECT status::text FROM public.refunds WHERE booking_id = :id", id=booking_id)
    assert refund_status == "SUCCEEDED"
