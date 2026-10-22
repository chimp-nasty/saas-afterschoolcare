"""
Approved children in the medical review list (Admin › Medical reviews):
admins list them newest decision first with who approved them, search any
list by the child's or the parent's name, and reopen an approved child for
review. Reopening sends the child back to waiting on staff, always sends
the family a message in their account (the admin's, or a default),
records a staff note, and leaves existing bookings booked; new bookings
wait for approval again.
"""

from app.integrations.email.messages import DocumentsRequestedEmail
from tests.factories import Api


BASE = "/medical-reviews/v1"


def _decide(client, child_id: str, decision: str, message: str | None = None):
    return client.post(f"{BASE}/{child_id}", json={"decision": decision, "message": message})


def _approved_child(api: Api, admin, customer, **child) -> dict:
    created = api.new_child(customer, allergy_info="Peanuts", **child)
    assert _decide(admin, created["id"], "approved").status_code == 200

    return created


# The approved list shows approved children, newest decision first, with
# who approved them.
def test_approved_list(api: Api, admin, customer):
    first = _approved_child(api, admin, customer)
    second = _approved_child(api, admin, customer)

    listed = admin.get(f"{BASE}/", params={"review_status": "approved"}).json()["data"]
    ids = [c["child_id"] for c in listed]

    assert ids.index(second["id"]) < ids.index(first["id"])
    assert next(c for c in listed if c["child_id"] == first["id"])["reviewed_by"]


# Any list can be searched by the start of the child's or the parent's
# name; another family's children don't match.
def test_search_by_name(api: Api, admin, customer):
    child = _approved_child(api, admin, customer, first_name="Wilhelmina")
    _approved_child(api, admin, api.new_customer(), first_name="Bartholomew")

    def search(q: str) -> list[str]:
        response = admin.get(f"{BASE}/", params={"review_status": "approved", "q": q})
        assert response.status_code == 200, response.text

        return [c["child_id"] for c in response.json()["data"]]

    assert search("wilhel") == [child["id"]]
    assert child["id"] in search(f"Wilhelmina {child['last_name'][:3]}")
    assert child["id"] in search("Test Cust")  # the parent's full name
    assert admin.get(f"{BASE}/", params={"q": "w"}).status_code == 422


# Reopening an approved child sends them back to waiting on staff with no
# reviewer, sends the family the admin's message in their account (no
# email), and adds a staff note.
def test_reopen(api: Api, admin, customer, sent_emails):
    child = _approved_child(api, admin, customer)
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    response = _decide(admin, child["id"], "reopen", "Please check the action plan is still current.")
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert (data["review_status"], data["reviewed_by_user_id"]) == ("pending", None)

    [action, *_] = customer.client.get("/action/v1/").json()["data"]
    assert (action["child_id"], action["target"]) == (child["id"], "profile")
    assert action["message"] == "Please check the action plan is still current."

    notes = admin.get(f"/families/v1/{user_id}/notes").json()["data"]
    assert notes[0]["note"] == "Reopened for medical review; the family was sent a message."
    assert sent_emails(DocumentsRequestedEmail) == []


# Without a message, the family is told staff are reviewing.
def test_reopen_without_a_message(api: Api, admin, customer):
    child = _approved_child(api, admin, customer)

    assert _decide(admin, child["id"], "reopen").status_code == 200

    [action, *_] = customer.client.get("/action/v1/").json()["data"]
    assert action["message"].startswith("Our staff are reviewing")


# Only an approved child can be reopened.
def test_only_approved_children_reopen(api: Api, admin, customer):
    child = api.new_child(customer, allergy_info="Peanuts")

    assert _decide(admin, child["id"], "reopen").status_code == 409


# Reopening leaves existing bookings booked (the review page counts them),
# but new bookings wait until the child is approved again.
def test_reopen_keeps_bookings(api: Api, admin, customer):
    child = _approved_child(api, admin, customer)
    booking_id = api.booking_on(customer, child["id"], days_from_today=1)

    review = admin.get(f"{BASE}/{child['id']}").json()["data"]
    assert review["upcoming_bookings"] == 1

    _decide(admin, child["id"], "reopen")

    [(status,)] = api.sql("SELECT booking_status::text FROM public.bookings WHERE id = :id", id=booking_id)
    assert status == "CONFIRMED"
    assert api.book(customer, {child["id"]: [api.service_day()]}).status_code == 400
