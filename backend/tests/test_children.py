from tests.factories import Api


def test_create_child(api: Api, customer):
    child = api.new_child(customer)

    assert child["review_status"] == "not_required"
    assert child["is_active"] is True


def test_child_with_medical_info_needs_review(api: Api, customer):
    child = api.new_child(customer, medical_info="Asthma")

    assert child["review_status"] == "pending"


def test_create_child_requires_complete_profile(api: Api):
    customer = api.new_customer(complete_profile=False)

    response = customer.client.post(
        "/children/v1/",
        json={
            "first_name": "Child",
            "last_name": "Test",
            "dob": "2019-03-01",
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
        },
    )

    assert response.status_code == 400
    assert "Missing: phone" in response.json()["msg"]


def test_duplicate_child_is_case_insensitive(api: Api, customer):
    api.new_child(customer, first_name="Emma", last_name="Smith", dob="2018-05-14")

    response = customer.client.post(
        "/children/v1/",
        json={
            "first_name": "emma",
            "last_name": "SMITH",
            "dob": "2018-05-14",
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
        },
    )

    assert response.status_code == 409


def test_get_child(api: Api, customer):
    child = api.new_child(customer)

    response = customer.client.get(f"/children/v1/{child['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == child["id"]


def test_get_unknown_child(customer):
    response = customer.client.get(
        "/children/v1/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_list_children_filters_by_review_status(api: Api, customer):
    plain = api.new_child(customer)
    needs_review = api.new_child(customer, allergy_info="Peanuts")

    response = customer.client.get(
        "/children/v1/",
        params={"review_status": "pending"},
    )

    ids = [child["id"] for child in response.json()["data"]]
    assert needs_review["id"] in ids
    assert plain["id"] not in ids
