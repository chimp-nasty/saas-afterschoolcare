import uuid

from tests.factories import Api


# Stripe is replaced by tests.factories.FakeStripe for every test (conftest).


def _service_id(admin, name: str) -> str:
    services = admin.get("/location-services/v1/").json()["data"]
    return next(s["id"] for s in services if s["service_name"] == name)


# A customer can list the location's services (the dev seed has four).
def test_list_location_services(customer):
    response = customer.client.get("/location-services/v1/")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 4


# An admin can change a service's price when it's linked to a Stripe
# product, and the new price shows in the list. The service is put back
# afterwards, since other tests share it.
def test_update_price(api: Api, admin):
    service_id = _service_id(admin, "Weekend Care")
    [(product, price, currency)] = api.sql(
        "SELECT stripe_product_id, current_price_cents, currency "
        "FROM public.location_services WHERE id = :id",
        id=service_id,
    )
    api.sql(
        "UPDATE public.location_services SET stripe_product_id = :product WHERE id = :id",
        product=f"prod_test_{uuid.uuid4().hex[:8]}",
        id=service_id,
    )

    try:
        response = admin.patch(
            f"/location-services/v1/{service_id}/price",
            json={"amount_cents": 7500, "currency": "AUD"},
        )

        assert response.status_code == 200
        services = admin.get("/location-services/v1/").json()["data"]
        assert next(s for s in services if s["id"] == service_id)["current_price_cents"] == 7500
    finally:
        api.sql(
            "UPDATE public.location_services "
            "SET stripe_product_id = :product, current_price_cents = :price, currency = :currency "
            "WHERE id = :id",
            product=product,
            price=price,
            currency=currency,
            id=service_id,
        )


# A price can't be changed for a service that isn't linked to a Stripe
# product (400).
def test_update_price_requires_stripe_product(admin):
    # The dev seed doesn't link Vacation Care to Stripe.
    response = admin.patch(
        f"/location-services/v1/{_service_id(admin, 'Vacation Care')}/price",
        json={"amount_cents": 7500, "currency": "AUD"},
    )

    assert response.status_code == 400


# Changing the price of a service that doesn't exist returns 404.
def test_update_price_unknown_service(admin):
    response = admin.patch(
        "/location-services/v1/00000000-0000-0000-0000-000000000000/price",
        json={"amount_cents": 7500, "currency": "AUD"},
    )

    assert response.status_code == 404


# The service days list returns every matching day rather than stopping at a
# default page size (more than 25 open days).
def test_list_service_days_is_not_capped(customer):
    response = customer.client.get(
        "/location-service-days/v1/",
        params={"is_open": True},
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) > 25
