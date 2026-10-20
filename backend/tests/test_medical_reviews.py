"""
Staff medical review (schema/0004, trg_child_medical_state_rules): staff
approve a child or ask the family for documentation; the family is told
through an action, and uploading a document sends the child back to staff.
A child with medical details can't be booked until approved.
"""

from app.integrations.email.messages import ChildApprovedEmail, DocumentsRequestedEmail
from tests.factories import Api, FakeStorage


PDF = b"%PDF-1.7\n" + b"0" * 200


def _decide(client, child_id: str, decision: str, message: str | None = None):
    return client.post(
        f"/medical-reviews/v1/{child_id}",
        json={"decision": decision, "message": message},
    )


def _queue(client, **params) -> list[dict]:
    response = client.get("/medical-reviews/v1/", params=params)
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _actions(customer) -> list[dict]:
    response = customer.client.get("/action/v1/")
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _upload(customer, child_id: str):
    response = customer.client.post(
        "/child-documents/v1/",
        json={
            "child_id": child_id,
            "document_type": "asthma_action_plan",
            "filename": "plan.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(PDF),
        },
    )
    assert response.status_code == 201, response.text

    started = response.json()["data"]
    assert FakeStorage.receive(started["upload"], PDF)

    response = customer.client.post(f"/child-documents/v1/{started['document']['id']}/complete")
    assert response.status_code == 200, response.text


# A child with medical details waits in the staff list with their family's
# contact details; a child without any isn't there.
def test_children_awaiting_review_are_listed(api: Api, customer, admin):
    waiting = api.new_child(customer, allergy_info="Peanuts")
    no_details = api.new_child(customer)

    rows = {row["child_id"]: row for row in _queue(admin)}

    assert waiting["id"] in rows
    assert no_details["id"] not in rows

    row = rows[waiting["id"]]
    assert row["review_status"] == "pending"
    assert row["family_phone"] == customer.phone
    assert row["document_count"] == 0


# Staff see one child's review: the medical details and the family.
def test_staff_see_a_childs_review(api: Api, customer, admin):
    child = api.new_child(customer, medication_info="Ventolin")

    response = admin.get(f"/medical-reviews/v1/{child['id']}")
    assert response.status_code == 200, response.text

    review = response.json()["data"]
    assert review["medication_info"] == "Ventolin"
    assert review["family_email"] == customer.email
    assert review["reviewed_by_user_id"] is None


# Approving clears the child for bookings, records who decided, and tells
# the family.
def test_staff_approve_a_child(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")

    response = _decide(admin, child["id"], "approved")
    assert response.status_code == 200, response.text

    review = response.json()["data"]
    assert review["review_status"] == "approved"
    assert review["reviewed_by_user_id"] is not None

    assert child["id"] not in {row["child_id"] for row in _queue(admin)}
    assert [a["title"] for a in _actions(customer)] == [f"{child['first_name']} is cleared for bookings"]

    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 201, response.text


# Approving an already-approved child changes nothing, so the family isn't
# told twice.
def test_approving_again_sends_nothing_new(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")

    _decide(admin, child["id"], "approved")
    response = _decide(admin, child["id"], "approved")
    assert response.status_code == 200, response.text

    assert len(_actions(customer)) == 1


# Asking for documentation needs a message saying what's needed.
def test_documentation_request_needs_a_message(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")

    response = _decide(admin, child["id"], "documentation_requested", "   ")
    assert response.status_code == 400, response.text

    response = admin.get(f"/medical-reviews/v1/{child['id']}")
    assert response.json()["data"]["review_status"] == "pending"


# Asking for documentation shows the family what's needed on the child,
# and sends them an action linking to the child's documents.
def test_staff_request_documentation(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")
    message = "Please upload Sam's signed asthma action plan."

    response = _decide(admin, child["id"], "documentation_requested", message)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["review_status"] == "documentation_requested"

    response = customer.client.get(f"/children/v1/{child['id']}")
    assert response.json()["data"]["review_status"] == "documentation_requested"
    assert response.json()["data"]["documentation_request"] == message

    [action] = _actions(customer)
    assert action["title"] == f"Documents needed for {child['first_name']}"
    assert action["message"] == message
    assert action["target"] == "manage-documents"
    assert action["child_id"] == child["id"]

    # Still can't be booked.
    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 400, response.text


# When the family uploads a document, the child goes back to staff, who
# can still see what they asked for.
def test_uploading_answers_a_documentation_request(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")
    message = "Please upload the action plan."
    _decide(admin, child["id"], "documentation_requested", message)

    _upload(customer, child["id"])

    [row] = [row for row in _queue(admin) if row["child_id"] == child["id"]]
    assert row["review_status"] == "pending"
    assert row["documentation_request"] == message
    assert row["document_count"] == 1

    # Approving clears the request.
    response = _decide(admin, child["id"], "approved")
    assert response.json()["data"]["documentation_request"] is None


# Staff can ask for documentation after approving (e.g. a plan has
# expired), which stops new bookings again.
def test_staff_can_request_documentation_after_approval(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")
    _decide(admin, child["id"], "approved")

    response = _decide(admin, child["id"], "documentation_requested", "The plan has expired.")
    assert response.status_code == 200, response.text

    response = api.book(customer, {child["id"]: [api.service_day()]})
    assert response.status_code == 400, response.text


# Staff only approve or request documentation; "pending" and
# "not_required" follow the child's details.
def test_staff_cannot_set_other_statuses(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")

    for status in ("pending", "not_required"):
        response = _decide(admin, child["id"], status)
        assert response.status_code == 422, response.text


# Families can't decide their own child's review.
def test_family_cannot_decide(api: Api, customer):
    child = api.new_child(customer, medical_info="Asthma")

    response = _decide(customer.client, child["id"], "approved")
    assert response.status_code == 403, response.text


# A family reaching the review list sees only their own children.
def test_family_sees_only_their_own_children(api: Api, customer, other_customer):
    mine = api.new_child(customer, medical_info="Asthma")
    theirs = api.new_child(other_customer, medical_info="Asthma")

    ids = {row["child_id"] for row in _queue(customer.client)}

    assert mine["id"] in ids
    assert theirs["id"] not in ids


# Staff at another tenant can't see or decide a child's review.
def test_other_tenant_cannot_review(api: Api, customer, tenant2_admin):
    child = api.new_child(customer, medical_info="Asthma")

    assert child["id"] not in {row["child_id"] for row in _queue(tenant2_admin)}
    assert tenant2_admin.get(f"/medical-reviews/v1/{child['id']}").status_code == 404
    assert _decide(tenant2_admin, child["id"], "approved").status_code == 404


# A removed child can't be reviewed.
def test_removed_child_cannot_be_reviewed(api: Api, customer, admin):
    child = api.new_child(customer, medical_info="Asthma")
    customer.client.post(f"/children/v1/{child['id']}/deactivate")

    response = _decide(admin, child["id"], "approved")
    assert response.status_code == 409, response.text


# Approving emails the family that the child can be booked: to the account
# holder, as the child's centre, with the child's first name only.
def test_approval_emails_the_family(api: Api, customer, admin, sent_emails):
    child = api.new_child(customer, medical_info="Asthma")

    _decide(admin, child["id"], "approved")

    [email] = sent_emails(ChildApprovedEmail)
    assert email.to_email == customer.email
    assert email.child_first_name == child["first_name"]
    assert str(email.location_id) == child["location_id"]


# Requesting documents emails the family a link to the child's documents,
# without the staff message (it stays in the app).
def test_documentation_request_emails_without_the_message(api: Api, customer, admin, sent_emails):
    child = api.new_child(customer, medical_info="Asthma")

    _decide(admin, child["id"], "documentation_requested", "Please upload the asthma plan.")

    [email] = sent_emails(DocumentsRequestedEmail)
    assert str(email.child_id) == child["id"]
    assert "asthma" not in repr(email).lower()


# Approving an approved child again sends nothing new.
def test_approving_again_emails_nothing_new(api: Api, customer, admin, sent_emails):
    child = api.new_child(customer, medical_info="Asthma")

    _decide(admin, child["id"], "approved")
    _decide(admin, child["id"], "approved")

    assert len(sent_emails(ChildApprovedEmail)) == 1


# A decision the database refuses (a request with no message) emails
# nobody.
def test_refused_decision_emails_nobody(api: Api, customer, admin, sent_emails):
    child = api.new_child(customer, medical_info="Asthma")

    response = _decide(admin, child["id"], "documentation_requested", "   ")
    assert response.status_code == 400, response.text

    assert sent_emails(ChildApprovedEmail, DocumentsRequestedEmail) == []
