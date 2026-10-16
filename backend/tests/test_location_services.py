import uuid

import pytest

from app.integrations.payments.stripe.client import StripePrice
from tests.factories import Api


class FakeStripe:
    def create_price(self, *, stripe_product_id, amount_cents, currency):
        return StripePrice(amount_cents=amount_cents, currency=currency.upper())


@pytest.fixture
def fake_stripe(monkeypatch):
    monkeypatch.setattr(
        "app.public.services.location_service.StripeClient",
        FakeStripe,
    )


def _service_id(admin, name: str) -> str:
    services = admin.get("/location-services/v1/").json()["data"]
    return next(s["id"] for s in services if s["service_name"] == name)


def test_list_location_services(customer):
    response = customer.client.get("/location-services/v1/")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 4


def test_list_is_scoped_to_the_session_location(admin):
    # t1user is admin at two tenant1 locations; only this session's shows.
    response = admin.get("/location-services/v1/")

    assert len(response.json()["data"]) == 4


def test_update_price(api: Api, admin, fake_stripe):
    service_id = _service_id(admin, "Weekend Care")
    api.sql(
        "UPDATE public.location_services SET stripe_product_id = :product WHERE id = :id",
        product=f"prod_test_{uuid.uuid4().hex[:8]}",
        id=service_id,
    )

    response = admin.patch(
        f"/location-services/v1/{service_id}/price",
        json={"amount_cents": 7500, "currency": "AUD"},
    )

    assert response.status_code == 200
    services = admin.get("/location-services/v1/").json()["data"]
    assert next(s for s in services if s["id"] == service_id)["current_price_cents"] == 7500


def test_update_price_requires_stripe_product(admin, fake_stripe):
    # The dev seed doesn't link Vacation Care to Stripe.
    response = admin.patch(
        f"/location-services/v1/{_service_id(admin, 'Vacation Care')}/price",
        json={"amount_cents": 7500, "currency": "AUD"},
    )

    assert response.status_code == 400


def test_update_price_unknown_service(admin, fake_stripe):
    response = admin.patch(
        "/location-services/v1/00000000-0000-0000-0000-000000000000/price",
        json={"amount_cents": 7500, "currency": "AUD"},
    )

    assert response.status_code == 404


def test_list_service_days_is_not_capped(customer):
    response = customer.client.get(
        "/location-service-days/v1/",
        params={"is_open": True},
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) > 25
