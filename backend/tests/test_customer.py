from tests.factories import COMPLETE_PROFILE, Api


def test_signup_duplicate_email(api: Api, customer):
    response = api.client().post(
        "/customer/v1/onboard/location1",
        json={
            "email": customer.email,
            "password": "Password123",
            "first_name": "Again",
            "last_name": "Customer",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 409


def test_signup_requires_terms(api: Api):
    response = api.client().post(
        "/customer/v1/onboard/location1",
        json={
            "email": "no-terms@test.com",
            "password": "Password123",
            "first_name": "No",
            "last_name": "Terms",
            "terms_accepted": False,
        },
    )

    assert response.status_code == 422


def test_new_profile_starts_empty(api: Api):
    customer = api.new_customer(complete_profile=False)

    response = customer.client.get("/customer/v1/profile")

    assert response.status_code == 200
    assert response.json()["data"]["phone"] is None


def test_update_profile(customer):
    response = customer.client.get("/customer/v1/profile")

    assert response.status_code == 200
    data = response.json()["data"]
    assert {key: data[key] for key in COMPLETE_PROFILE} == COMPLETE_PROFILE


def test_update_profile_rejects_unknown_state(customer):
    response = customer.client.patch(
        "/customer/v1/profile",
        json={"state": "XX"},
    )

    assert response.status_code == 422
