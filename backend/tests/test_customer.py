from tests.factories import COMPLETE_PROFILE, Api


# Signing up with an email that already has an account is refused (409).
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


# Signing up without accepting the terms is rejected as invalid (422).
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


# A newly signed-up customer's profile has no contact details yet (phone is
# empty).
def test_new_profile_starts_empty(api: Api):
    customer = api.new_customer(complete_profile=False)

    response = customer.client.get("/customer/v1/profile")

    assert response.status_code == 200
    assert response.json()["data"]["phone"] is None


# Updating one field returns the updated profile, and reading it back shows
# the change with every other field left as it was.
def test_update_profile(customer):
    response = customer.client.patch(
        "/customer/v1/profile",
        json={"suburb": "Toowong"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["suburb"] == "Toowong"

    data = customer.client.get("/customer/v1/profile").json()["data"]
    expected = {**COMPLETE_PROFILE, "phone": customer.phone, "suburb": "Toowong"}
    assert {key: data[key] for key in expected} == expected


# Saving an Australian state that doesn't exist ('XX') is rejected as
# invalid (422).
def test_update_profile_rejects_unknown_state(customer):
    response = customer.client.patch(
        "/customer/v1/profile",
        json={"state": "XX"},
    )

    assert response.status_code == 422
