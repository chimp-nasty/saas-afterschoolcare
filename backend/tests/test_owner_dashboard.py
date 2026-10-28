"""
The owner dashboard (docs/owner-dashboard.md): the business owner sees a
period's numbers (sessions by when they take place; sign-ups, refunds and
cancellations by when they happened), the period before, what needs
attention, and payments to refund in Stripe. Only the owner, only their
own business. The test database is shared, so each test measures a number,
does one thing, and checks it moved by exactly that.
"""

import pytest

from tests.factories import Api


BASE = "/business/v1/dashboard"


def _location1_id(api: Api) -> str:
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )

    return location_id


def _dashboard(api: Api, owner, week: int | None = 0) -> dict:
    params = {"all_time": "true"} if week is None else {"week": week}
    response = owner.get(BASE, params={**params, "location_id": _location1_id(api)})
    assert response.status_code == 200, response.text

    return response.json()["data"]


# A paid session today counts this week: one more booking, its price on the
# revenue, and its family active.
def test_a_session_this_week_counts(api: Api, owner):
    before = _dashboard(api, owner)["current"]
    family = api.new_customer()
    booking_id = api.booking_today(family, api.new_child(family)["id"])
    [(price,)] = api.sql("SELECT price_snapshot_cents FROM public.bookings WHERE id = :id", id=booking_id)

    after = _dashboard(api, owner)["current"]

    assert after["bookings"] == before["bookings"] + 1
    assert after["revenue_cents"] == before["revenue_cents"] + price
    assert after["active_families"] == before["active_families"] + 1


# A new family account counts as a registration this week.
def test_a_new_family_is_a_registration(api: Api, owner):
    before = _dashboard(api, owner)["current"]["registrations"]

    api.new_customer()

    assert _dashboard(api, owner)["current"]["registrations"] == before + 1


# A refunded session comes off the revenue, and the refund counts this week.
def test_a_refund_counts_and_comes_off_revenue(api: Api, owner, admin, fake_stripe):
    family = api.new_customer()
    booking_id = api.booking_today(family, api.new_child(family)["id"])
    before = _dashboard(api, owner)["current"]

    assert admin.post("/refunds/v1/", json={"booking_id": booking_id}).status_code == 201
    [stripe_refund_id] = list(fake_stripe.state.refunds)
    api.refund_webhook("refund.updated", stripe_refund_id, status="succeeded")

    after = _dashboard(api, owner)["current"]
    [(price,)] = api.sql("SELECT price_snapshot_cents FROM public.bookings WHERE id = :id", id=booking_id)

    assert after["refunds"] == before["refunds"] + 1
    assert after["refunded_cents"] == before["refunded_cents"] + price
    assert after["revenue_cents"] == before["revenue_cents"] - price
    assert after["bookings"] == before["bookings"] - 1


# A week still to come: its sign-ups, refunds and cancellations are none
# (not 0), and it's compared with the week before. Any week can be shown,
# a week apart. All time has no week and nothing to compare with.
def test_future_weeks_and_all_time(api: Api, owner):
    next_week = _dashboard(api, owner, 1)
    this_week = _dashboard(api, owner, 0)
    five_weeks_ago = _dashboard(api, owner, -5)
    all_time = _dashboard(api, owner, None)

    assert next_week["current"]["registrations"] is None
    assert next_week["current"]["refunds"] is None
    assert next_week["previous"]["bookings"] == this_week["current"]["bookings"]
    assert next_week["from_date"] > this_week["from_date"] > five_weeks_ago["from_date"]
    assert five_weeks_ago["week"] == -5
    assert five_weeks_ago["current"]["registrations"] is not None

    assert all_time["previous"] is None
    assert all_time["from_date"] is None
    assert all_time["current"]["bookings"] >= this_week["current"]["bookings"]


# A new enquiry shows as a follow-up until it's replied to.
def test_new_enquiries_need_attention(api: Api, owner, admin):
    before = _dashboard(api, owner)["attention"]["enquiries_new"]

    response = api.client().post(
        "/enquiries/v1/location1/submit",
        json={"name": "Robin Doe", "email": "robin.doe@example.com", "topic": "general", "message": "Hello"},
    )
    assert response.status_code == 201, response.text
    assert _dashboard(api, owner)["attention"]["enquiries_new"] == before + 1

    [(enquiry_id,)] = api.sql("SELECT id::text FROM public.enquiries WHERE email = 'robin.doe@example.com' ORDER BY created_at DESC LIMIT 1")
    admin.post(f"/enquiries/v1/{enquiry_id}/reply", json={"body": "Thanks!"})

    assert _dashboard(api, owner)["attention"]["enquiries_new"] == before


# A payment that arrived after its places were released (the hold lapsed)
# is listed by its booking reference, to refund in Stripe.
def test_payments_needing_a_refund_are_listed(api: Api, owner, customer):
    child = api.new_child(customer)
    data = api.book(customer, {child["id"]: [api.service_day()]}).json()["data"]
    group_id = data["booking_group_id"]
    [(reference,)] = api.sql("SELECT reference FROM public.booking_groups WHERE id = :id", id=group_id)

    # The hold lapses before the payment is seen.
    api.sql("UPDATE public.bookings SET booking_status = 'EXPIRED', payment_status = 'FAILED' WHERE booking_group_id = :id", id=group_id)
    api.webhook("checkout.session.completed", api.session_id(data["checkout_url"]))

    listed = _dashboard(api, owner)["attention"]["unrefunded_payments"]

    assert reference in [payment["reference"] for payment in listed]


# Only the business's owner sees it: a centre admin and a family are
# refused (403), and another business's owner can't ask about this
# business's centre (404).
def test_only_the_owner_sees_it(api: Api, admin, customer, tenant2_owner):
    assert admin.get(BASE).status_code == 403
    assert customer.client.get(BASE).status_code == 403
    assert tenant2_owner.get(BASE, params={"location_id": _location1_id(api)}).status_code == 404


# All centres together count at least as much as one of them.
def test_all_centres(api: Api, owner):
    one = _dashboard(api, owner)["current"]
    response = owner.get(BASE)

    assert response.status_code == 200, response.text
    assert response.json()["data"]["current"]["bookings"] >= one["bookings"]


# A week has to be a whole number, at most ten years back or two ahead (422).
@pytest.mark.parametrize("week", ["yesterday", "1.5", "-521", "105"])
def test_unknown_weeks_are_refused(owner, week):
    assert owner.get(BASE, params={"week": week}).status_code == 422
