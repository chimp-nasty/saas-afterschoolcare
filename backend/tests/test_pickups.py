"""
A family's pickup list (schema/0004): the account holder plus up to three
people who may collect every child on the account. Each person is a future
kiosk login keyed by phone, so a phone number belongs to one family.
"""

from tests.factories import Api, new_phone


def _pickups(customer) -> list[dict]:
    response = customer.client.get("/pickups/v1/")
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _add(customer, **overrides):
    return customer.client.post(
        "/pickups/v1/",
        json={
            "first_name": "Mary",
            "last_name": "Smith",
            "phone": new_phone(),
            "relation": "grandparent",
            "consent_confirmed": True,
            "adult_confirmed": True,
            **overrides,
        },
    )


def _added(customer, **overrides) -> dict:
    response = _add(customer, **overrides)
    assert response.status_code == 201, response.text

    return response.json()["data"]


def _update(customer, pickup_id: str, **body):
    return customer.client.patch(f"/pickups/v1/{pickup_id}", json=body)


def _deactivate(customer, pickup_id: str):
    return customer.client.post(f"/pickups/v1/{pickup_id}/deactivate")


def _check_id(api: Api, pickup_id: str):
    """Staff check the person's ID (no staff API yet)."""
    api.sql(
        "UPDATE public.authorized_pickup_persons SET identity_verified_at = now() WHERE id = :id",
        id=pickup_id,
    )


def _set_pin(api: Api, pickup_id: str):
    """The person chooses their own kiosk PIN (no kiosk API yet)."""
    api.sql(
        "UPDATE public.authorized_pickup_persons SET pin_hash = 'chosen' WHERE id = :id",
        id=pickup_id,
    )


def _holder(customer) -> dict:
    [holder] = [p for p in _pickups(customer) if p["is_account_holder"]]

    return holder


# ---------------------------------------------------------------------------
# The list
# ---------------------------------------------------------------------------

# The account holder is on their own list automatically, from their profile.
def test_account_holder_is_on_the_list(customer):
    [holder] = _pickups(customer)

    assert holder["is_account_holder"] is True
    assert holder["relation"] == "account_holder"
    assert holder["first_name"] == "Test"
    assert holder["phone"] == customer.phone


# A family can add a pickup person; they start unchecked, on the default
# kiosk PIN, with their phone stored as digits only.
def test_add_pickup_person(customer):
    phone = new_phone()
    spaced = f"{phone[:4]} {phone[4:7]} {phone[7:]}"

    person = _added(customer, phone=spaced)

    assert person["phone"] == phone
    assert person["is_account_holder"] is False
    assert person["identity_verified"] is False
    assert person["kiosk_pin_set"] is False
    assert [p["id"] for p in _pickups(customer)][1:] == [person["id"]]


# Both declarations (they agreed, and they're over 18) must be ticked.
def test_both_declarations_are_required(customer):
    for declaration in ("consent_confirmed", "adult_confirmed"):
        assert _add(customer, **{declaration: False}).status_code == 422, declaration


# "Other" needs its own description; the account holder can't be added by hand.
def test_relationship_rules(customer):
    assert _add(customer, relation="other").status_code == 422
    assert _add(customer, relation="account_holder").status_code == 422

    person = _added(customer, relation="other", relation_other="Godmother")
    assert person["relation_other"] == "Godmother"


# At most three people besides the account holder; removing one frees a place.
def test_limit_of_three(customer):
    people = [_added(customer) for _ in range(3)]

    response = _add(customer)
    assert response.status_code == 409
    assert "up to 3 pickup people" in response.json()["msg"]

    _deactivate(customer, people[0]["id"])
    assert _add(customer).status_code == 201


# ---------------------------------------------------------------------------
# One phone number, one family
# ---------------------------------------------------------------------------

# A phone number on another family's list (or another account holder's
# phone) can't be added.
def test_phone_belongs_to_one_family(customer, other_customer):
    theirs = _added(other_customer)

    for phone in (theirs["phone"], other_customer.phone):
        response = _add(customer, phone=phone)

        assert response.status_code == 409
        assert "already registered at this centre" in response.json()["msg"]


# A family can't list the same phone twice.
def test_phone_listed_once_per_family(customer):
    person = _added(customer)

    response = _add(customer, phone=person["phone"])

    assert response.status_code == 409
    assert "already on your pickup list" in response.json()["msg"]


# Someone removed from the list can be added again.
def test_readding_a_removed_person(customer):
    person = _added(customer)
    _deactivate(customer, person["id"])

    assert _add(customer, phone=person["phone"]).status_code == 201


# An account holder can't change their profile phone to one another family
# already uses (their pickup row follows the profile).
def test_profile_phone_taken_by_another_family(customer, other_customer):
    theirs = _added(other_customer)

    response = customer.client.patch("/customer/v1/profile", json={"phone": theirs["phone"]})

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Editing and removing
# ---------------------------------------------------------------------------

# A new name means staff check their ID again; a new relationship doesn't.
def test_name_change_resets_the_id_check(api: Api, customer):
    person = _added(customer)
    _check_id(api, person["id"])

    response = _update(customer, person["id"], relation="aunt_uncle")
    assert response.json()["data"]["identity_verified"] is True

    response = _update(customer, person["id"], first_name="Maria")
    assert response.status_code == 200
    assert response.json()["data"]["identity_verified"] is False


# A new phone is a new kiosk login: the ID check and the PIN both reset.
def test_phone_change_resets_the_id_check_and_pin(api: Api, customer):
    person = _added(customer)
    _check_id(api, person["id"])
    _set_pin(api, person["id"])

    response = _update(customer, person["id"], phone=new_phone())

    assert response.status_code == 200
    assert response.json()["data"]["identity_verified"] is False
    assert response.json()["data"]["kiosk_pin_set"] is False


# The account holder's row comes from their profile: it can't be edited or
# removed here.
def test_account_holder_row_cannot_be_edited_or_removed(customer):
    holder = _holder(customer)

    assert _update(customer, holder["id"], first_name="Someone").status_code == 400
    assert _deactivate(customer, holder["id"]).status_code == 400


# Changing the profile phone updates the account holder's row, which then
# needs its ID checked again.
def test_account_holder_row_follows_the_profile_phone(api: Api, customer):
    _check_id(api, _holder(customer)["id"])
    phone = new_phone()

    assert customer.client.patch("/customer/v1/profile", json={"phone": phone}).status_code == 200

    holder = _holder(customer)
    assert holder["phone"] == phone
    assert holder["identity_verified"] is False


# Removed people leave the list.
def test_deactivate_pickup_person(customer):
    person = _added(customer)

    assert _deactivate(customer, person["id"]).status_code == 200
    assert person["id"] not in [p["id"] for p in _pickups(customer)]


# Another family's pickup people can't be seen, edited or removed (404).
def test_pickups_are_private(customer, other_customer):
    person = _added(customer)

    assert person["id"] not in [p["id"] for p in _pickups(other_customer)]
    assert other_customer.client.get(f"/pickups/v1/{person['id']}").status_code == 404
    assert _update(other_customer, person["id"], first_name="Nope").status_code == 404
    assert _deactivate(other_customer, person["id"]).status_code == 404


# ---------------------------------------------------------------------------
# New children and who may add
# ---------------------------------------------------------------------------

# Adding a child extends the pickup list to them, so the account holder must
# agree when there's anyone on it besides themselves.
def test_new_child_needs_consent_for_the_pickup_list(api: Api, customer):
    api.new_child(customer)

    _added(customer)

    response = customer.client.post(
        "/children/v1/",
        json={
            "first_name": "No",
            "last_name": "Consent",
            "dob": "2016-01-01",
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
        },
    )
    assert response.status_code == 400
    assert "pickup list" in response.json()["msg"]

    api.new_child(customer, pickup_consent=True)


# Only families add children and pickup people: admins can't (403).
def test_admin_cannot_add_children_or_pickups(admin):
    child = admin.post(
        "/children/v1/",
        json={
            "first_name": "Admin",
            "last_name": "Child",
            "dob": "2016-01-01",
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
        },
    )
    pickup = admin.post(
        "/pickups/v1/",
        json={
            "first_name": "Admin",
            "last_name": "Pickup",
            "phone": new_phone(),
            "relation": "grandparent",
            "consent_confirmed": True,
            "adult_confirmed": True,
        },
    )

    assert child.status_code == 403
    assert pickup.status_code == 403
