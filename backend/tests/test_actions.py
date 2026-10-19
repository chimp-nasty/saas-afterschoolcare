import uuid

import pytest

from tests.factories import Api


@pytest.fixture
def customer_with_actions(api: Api, customer):
    """A customer with three uncited actions (actions have no create API)."""
    location = api.sql(
        "SELECT id FROM tenancy.locations WHERE code = 'location1' "
        "AND tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant1')"
    )[0][0]

    for n in range(3):
        api.sql(
            """
            INSERT INTO public.actions (
                user_id, location_id, target, title, message, created_by_user_id
            )
            SELECT u.id, :location_id, 'profile', :title, 'Please review.', u.id
            FROM auth.users u
            WHERE u.email = :email
            """,
            location_id=location,
            title=f"Action {n} {uuid.uuid4().hex[:6]}",
            email=customer.email,
        )

    return customer


# A customer can list their actions (to-dos raised for them) and sees all
# three created for them.
def test_list_actions(customer_with_actions):
    response = customer_with_actions.client.get("/action/v1/")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 3


# The actions list splits into pages: with two per page, page one has two,
# page two has the remaining one, and no action appears on both.
def test_list_actions_paginates(customer_with_actions):
    first = customer_with_actions.client.get(
        "/action/v1/", params={"page": 1, "limit": 2}
    ).json()["data"]
    second = customer_with_actions.client.get(
        "/action/v1/", params={"page": 2, "limit": 2}
    ).json()["data"]

    assert len(first) == 2
    assert len(second) == 1
    assert {a["id"] for a in first}.isdisjoint(a["id"] for a in second)


# Asking for more than the maximum page size (500 per page) is rejected as
# invalid instead of returning everything.
def test_list_actions_limit_is_capped(customer_with_actions):
    response = customer_with_actions.client.get(
        "/action/v1/", params={"limit": 500}
    )

    assert response.status_code == 422


# Marking an action as seen (cited) records when it was seen and drops the
# unseen count from three to two.
def test_marking_cited_updates_count(customer_with_actions):
    client = customer_with_actions.client
    [action, *_] = client.get("/action/v1/").json()["data"]

    assert client.get("/action/v1/count/uncited").json()["data"] == 3

    response = client.patch(f"/action/v1/{action['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["cited_at"] is not None
    assert client.get("/action/v1/count/uncited").json()["data"] == 2


# Marking an action that doesn't exist returns 404 not found.
def test_mark_unknown_action(customer):
    response = customer.client.patch(
        "/action/v1/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
