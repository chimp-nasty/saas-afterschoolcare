from contextlib import contextmanager
from datetime import date

from tests.factories import Api


def _dob(years_old: int) -> str:
    """A birthday that makes the child `years_old` today (born 1 Jan)."""
    return date(date.today().year - years_old, 1, 1).isoformat()


def _child(customer, child_id: str) -> dict:
    response = customer.client.get(f"/children/v1/{child_id}")
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _update(customer, child_id: str, **body):
    return customer.client.patch(f"/children/v1/{child_id}", json=body)


def _deactivate(customer, child_id: str):
    return customer.client.post(f"/children/v1/{child_id}/deactivate")


def _approve(api: Api, child_id: str):
    """Staff approve the child's medical review (no staff API yet)."""
    api.sql(
        "UPDATE public.child_medical_state SET review_status = 'approved' WHERE child_id = :id",
        id=child_id,
    )


@contextmanager
def _service_age_range(api: Api, min_age: int, max_age: int):
    """
    Set after-school care's age range at location1 for one test, then put
    it back (the service is shared by every test).
    """
    service = (
        "FROM public.service_types st, tenancy.locations l "
        "WHERE ls.service_type_id = st.id AND ls.location_id = l.id "
        "AND st.code = 'after_school_care' AND l.code = 'location1'"
    )
    [(original_min, original_max)] = api.sql(
        "SELECT ls.min_child_age, ls.max_child_age "
        "FROM public.location_services ls "
        "JOIN public.service_types st ON st.id = ls.service_type_id "
        "JOIN tenancy.locations l ON l.id = ls.location_id "
        "WHERE st.code = 'after_school_care' AND l.code = 'location1'"
    )
    set_range = (
        "UPDATE public.location_services ls "
        "SET min_child_age = :min_age, max_child_age = :max_age " + service
    )

    api.sql(set_range, min_age=min_age, max_age=max_age)
    try:
        yield
    finally:
        api.sql(set_range, min_age=original_min, max_age=original_max)


# A customer can add a child with no medical info; it's active and doesn't
# need staff review.
def test_create_child(api: Api, customer):
    child = api.new_child(customer)

    assert child["review_status"] == "not_required"
    assert child["is_active"] is True


# A child added with medical info is marked as needing staff review
# (pending).
def test_child_with_medical_info_needs_review(api: Api, customer):
    child = api.new_child(customer, medical_info="Asthma")

    assert child["review_status"] == "pending"


# A customer with an incomplete profile can't add a child, and is told
# what's missing.
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


# The same child can't be added twice, even with different capitalisation
# ('emma SMITH' vs 'Emma Smith', same birth date).
def test_duplicate_child_is_case_insensitive(api: Api, customer):
    api.new_child(customer, first_name="Emma", last_name="Smith", dob=_dob(10))

    response = customer.client.post(
        "/children/v1/",
        json={
            "first_name": "emma",
            "last_name": "SMITH",
            "dob": _dob(10),
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
        },
    )

    assert response.status_code == 409


# A customer can fetch one of their children by id.
def test_get_child(api: Api, customer):
    child = api.new_child(customer)

    response = customer.client.get(f"/children/v1/{child['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == child["id"]


# Fetching a child that doesn't exist returns 404.
def test_get_unknown_child(customer):
    response = customer.client.get(
        "/children/v1/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


# The children list can be filtered by review status: filtering for
# 'pending' includes the child with allergy info and leaves out the one
# without.
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


# ---------------------------------------------------------------------------
# Age range (location_services.min_child_age / max_child_age, default 8-17)
# ---------------------------------------------------------------------------

# A child too young or too old for every service at the location can't be
# added, and the message says the accepted range.
def test_child_must_be_within_the_locations_age_range(customer):
    for years_old in (7, 18):
        response = customer.client.post(
            "/children/v1/",
            json={
                "first_name": "Out",
                "last_name": f"Of Range {years_old}",
                "dob": _dob(years_old),
                "medical_info": None,
                "allergy_info": None,
                "medication_info": None,
            },
        )

        assert response.status_code == 400, years_old
        assert response.json()["msg"] == "Children must be aged 8 to 17"


# Each booking checks the child's age on the session date against that
# service's own range.
def test_booking_checks_the_services_age_range(api: Api, customer):
    child = api.new_child(customer, dob=_dob(10))

    with _service_age_range(api, 5, 9):
        response = api.book(customer, {child["id"]: [api.service_day()]})

    assert response.status_code == 400
    assert "age is outside this service's age range" in response.json()["msg"]


# ---------------------------------------------------------------------------
# Editing a child
# ---------------------------------------------------------------------------

# A family can fix a misspelt name; it doesn't affect the medical review.
def test_update_child_name(api: Api, customer):
    child = api.new_child(customer, first_name="Emmma")

    response = _update(customer, child["id"], first_name="Emma")

    assert response.status_code == 200
    assert response.json()["data"]["first_name"] == "Emma"
    assert response.json()["data"]["review_status"] == "not_required"


# The date of birth isn't editable: a dob in the request is ignored.
def test_date_of_birth_cannot_be_changed(api: Api, customer):
    child = api.new_child(customer)

    response = _update(customer, child["id"], dob=_dob(12))

    assert response.status_code == 200
    assert _child(customer, child["id"])["dob"] == child["dob"]


# Adding medical details to a child who already has bookings sends them
# back to review: the existing booking stays, new bookings are blocked.
def test_adding_medical_details_needs_review_again(api: Api, customer):
    child = api.new_child(customer)
    assert api.book(customer, {child["id"]: [api.service_day()]}).status_code == 201

    response = _update(customer, child["id"], allergy_info="Peanuts")

    assert response.status_code == 200
    assert response.json()["data"]["review_status"] == "pending"

    bookings = customer.client.get("/booking/v1/").json()["data"]
    assert [b["child_id"] for b in bookings] == [child["id"]]

    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 400
    assert "awaiting medical review" in response.json()["msg"]


# Editing or clearing already-approved medical details also needs review
# again, so staff see the change.
def test_changing_approved_medical_details_needs_review_again(api: Api, customer):
    for change in ("Asthma, mild", None):
        child = api.new_child(customer, medical_info="Asthma")
        _approve(api, child["id"])

        response = _update(customer, child["id"], medical_info=change)

        assert response.json()["data"]["review_status"] == "pending", change


# Saving medical details unchanged, or as blank text, isn't a change.
def test_unchanged_medical_details_keep_the_review(api: Api, customer):
    child = api.new_child(customer, medical_info="Asthma")
    _approve(api, child["id"])

    response = _update(customer, child["id"], medical_info="Asthma", allergy_info="  ")

    assert response.json()["data"]["review_status"] == "approved"


# Renaming a child to match a sibling with the same birthday is a
# duplicate, like adding them twice.
def test_rename_onto_a_sibling_is_a_duplicate(api: Api, customer):
    dob = _dob(10)
    api.new_child(customer, first_name="Ava", last_name="Twin", dob=dob)
    sibling = api.new_child(customer, first_name="Mia", last_name="Twin", dob=dob)

    response = _update(customer, sibling["id"], first_name="ava")

    assert response.status_code == 409


# A customer can't edit another customer's child (404).
def test_cannot_update_another_customers_child(api: Api, customer, other_customer):
    child = api.new_child(customer)

    assert _update(other_customer, child["id"], first_name="Nope").status_code == 404


# ---------------------------------------------------------------------------
# Removing a child (soft delete)
# ---------------------------------------------------------------------------

# Removing a child marks them inactive: they leave the active list, can't
# be edited, and can't be booked.
def test_deactivate_child(api: Api, customer):
    child = api.new_child(customer)

    response = _deactivate(customer, child["id"])

    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is False

    active = customer.client.get("/children/v1/", params={"is_active": True}).json()["data"]
    assert child["id"] not in [c["id"] for c in active]

    assert _update(customer, child["id"], first_name="Back").status_code == 409

    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 400
    assert response.json()["msg"] == "This child has been removed and can't be booked"


# A child with an upcoming booking can't be removed until it's cancelled.
def test_cannot_deactivate_with_upcoming_bookings(api: Api, customer):
    child = api.new_child(customer)
    group_id = api.book(customer, {child["id"]: [api.service_day()]}).json()["data"]["booking_group_id"]

    response = _deactivate(customer, child["id"])

    assert response.status_code == 409
    assert "upcoming bookings" in response.json()["msg"]

    customer.client.post(f"/booking/v1/groups/{group_id}/cancel")

    assert _deactivate(customer, child["id"]).status_code == 200


# A customer can't remove another customer's child (404).
def test_cannot_deactivate_another_customers_child(api: Api, customer, other_customer):
    child = api.new_child(customer)

    assert _deactivate(other_customer, child["id"]).status_code == 404
