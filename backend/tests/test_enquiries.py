"""
Contact form enquiries (docs/enquiries.md). Anyone sends one from a
centre's page; it's kept in the app, not emailed. The person gets a
receipt; the centre's optional enquiries address gets a notice (who and
what about, never the message). The centre's admins read, reply (emailed to
the person), close and reopen enquiries; nobody else sees them.
"""

import pytest

from app.integrations.email.messages import (
    EnquiryNoticeEmail,
    EnquiryReceivedEmail,
    EnquiryReplyEmail,
)
from tests.factories import Api


BASE = "/enquiries/v1"

ENQUIRY = {
    "name": "Alex Taylor",
    "email": "alex.taylor@example.com",
    "phone": "0412 345 678",
    "topic": "enrolment",
    "message": "Do you have places on Tuesdays for a 6 year old?",
}


def _send(client, **changes):
    return client.post(f"{BASE}/location1/submit", json={**ENQUIRY, **changes})


def _stored(api: Api, email: str = ENQUIRY["email"]) -> list[tuple]:
    return api.sql(
        "SELECT id::text, status::text, message FROM public.enquiries WHERE email = :email ORDER BY created_at",
        email=email,
    )


@pytest.fixture
def unique_email(api: Api):
    """Each test's enquiries under their own address, so they're its own."""
    import uuid

    return f"enquirer-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def notice_address(api: Api):
    """location1 also emails a notice of each enquiry; put back afterwards."""
    address = "enquiries@centre.example.com"
    api.sql(
        "UPDATE tenancy.locations l SET enquiry_notice_email = :a FROM tenancy.tenants t "
        "WHERE t.id = l.tenant_id AND t.code = 'tenant1' AND l.code = 'location1'",
        a=address,
    )

    yield address

    api.sql(
        "UPDATE tenancy.locations l SET enquiry_notice_email = NULL FROM tenancy.tenants t "
        "WHERE t.id = l.tenant_id AND t.code = 'tenant1' AND l.code = 'location1'"
    )


# ---------------------------------------------------------------------------
# Sending one
# ---------------------------------------------------------------------------

# Anyone can send an enquiry from the centre's page without logging in. It's
# kept as new, and they get a receipt that doesn't repeat what they wrote.
def test_anyone_sends_an_enquiry(api: Api, unique_email, sent_emails):
    response = _send(api.client(), email=unique_email)

    assert response.status_code == 201, response.text
    [(_, status, message)] = _stored(api, unique_email)
    assert (status, message) == ("new", ENQUIRY["message"])

    [receipt] = sent_emails(EnquiryReceivedEmail)
    assert receipt.to_email == unique_email
    assert receipt.first_name == "Alex"
    assert sent_emails(EnquiryNoticeEmail) == []


# A logged-in family can send one too.
def test_a_family_sends_an_enquiry(api: Api, customer, unique_email):
    assert _send(customer.client, email=unique_email).status_code == 201
    assert len(_stored(api, unique_email)) == 1


# With an enquiries address set, the centre is also told by email: who it's
# from and the topic, with a link into the app, never the message itself or
# how to contact them.
def test_the_centre_gets_a_notice(api: Api, unique_email, notice_address, sent_emails):
    assert _send(api.client(), email=unique_email).status_code == 201

    [notice] = sent_emails(EnquiryNoticeEmail)
    assert notice.to_email == notice_address
    assert notice.enquirer_first_name == "Alex"
    assert notice.topic == "enrolment"
    assert not hasattr(notice, "message") and not hasattr(notice, "phone")


# A form with the hidden field filled in (only bots see it) is told it was
# sent, but nothing is kept and nobody is emailed.
def test_the_spam_trap(api: Api, unique_email, sent_emails):
    response = _send(api.client(), email=unique_email, website="http://spam.example.com")

    assert response.status_code == 201
    assert _stored(api, unique_email) == []
    assert sent_emails(EnquiryReceivedEmail) == []


# A name, a valid email, a topic and a message are needed (422).
@pytest.mark.parametrize(
    "changes",
    [{"name": ""}, {"email": "not-an-email"}, {"topic": "complaints"}, {"message": ""}, {"message": "x" * 3001}],
)
def test_what_an_enquiry_needs(api: Api, changes):
    assert _send(api.client(), **changes).status_code == 422


# An enquiry to a centre that doesn't exist is a 404.
def test_unknown_centre(api: Api):
    response = api.client().post(f"{BASE}/no-such-centre/submit", json=ENQUIRY)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# The admins' inbox
# ---------------------------------------------------------------------------

def _enquiry_id(api: Api, unique_email: str) -> str:
    assert _send(api.client(), email=unique_email).status_code == 201
    [(enquiry_id, _, _)] = _stored(api, unique_email)

    return enquiry_id


# The centre's admins see new enquiries in their inbox, newest first, with
# the start of each message, and can open one to read it all.
def test_admins_read_enquiries(api: Api, admin, unique_email):
    enquiry_id = _enquiry_id(api, unique_email)

    listed = admin.get(f"{BASE}/").json()["data"]
    [row] = [e for e in listed if e["id"] == enquiry_id]
    assert (row["status"], row["preview"]) == ("new", ENQUIRY["message"])

    detail = admin.get(f"{BASE}/{enquiry_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["message"] == ENQUIRY["message"]
    assert detail.json()["data"]["replies"] == []


# Families can't see enquiries (403), and another business's admins can't
# find this centre's (404).
def test_only_the_centres_admins_see_enquiries(api: Api, customer, tenant2_admin, unique_email):
    enquiry_id = _enquiry_id(api, unique_email)

    assert customer.client.get(f"{BASE}/").status_code == 403
    assert tenant2_admin.get(f"{BASE}/{enquiry_id}").status_code == 404
    assert enquiry_id not in [e["id"] for e in tenant2_admin.get(f"{BASE}/").json()["data"]]


# An admin replies: it's kept with the enquiry (with who replied), the
# enquiry is marked replied, and the reply is emailed to the person as
# written. They can reply again.
def test_admin_replies(api: Api, admin, unique_email, sent_emails):
    enquiry_id = _enquiry_id(api, unique_email)

    response = admin.post(f"{BASE}/{enquiry_id}/reply", json={"body": "Yes, we have places on Tuesdays."})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "replied"
    assert [r["body"] for r in data["replies"]] == ["Yes, we have places on Tuesdays."]
    assert data["replies"][0]["staff_name"]

    [email] = sent_emails(EnquiryReplyEmail)
    assert (email.to_email, email.first_name, email.reply) == (unique_email, "Alex", "Yes, we have places on Tuesdays.")

    again = admin.post(f"{BASE}/{enquiry_id}/reply", json={"body": "Here's how to enrol."}).json()["data"]
    assert len(again["replies"]) == 2


# An empty reply is refused (422).
def test_a_reply_needs_words(api: Api, admin, unique_email):
    enquiry_id = _enquiry_id(api, unique_email)

    assert admin.post(f"{BASE}/{enquiry_id}/reply", json={"body": "  "}).status_code == 422


# Closing takes an enquiry off the open list; reopening puts it back as it
# was (new if never replied to, else replied). Replying to a closed one
# reopens it.
def test_closing_and_reopening(api: Api, admin, unique_email):
    enquiry_id = _enquiry_id(api, unique_email)

    closed = admin.post(f"{BASE}/{enquiry_id}/close").json()["data"]
    assert (closed["status"], closed["closed_at"] is not None) == ("closed", True)
    assert enquiry_id not in [e["id"] for e in admin.get(f"{BASE}/").json()["data"]]
    assert enquiry_id in [e["id"] for e in admin.get(f"{BASE}/", params={"status": "closed"}).json()["data"]]

    reopened = admin.post(f"{BASE}/{enquiry_id}/reopen").json()["data"]
    assert (reopened["status"], reopened["closed_at"]) == ("new", None)

    admin.post(f"{BASE}/{enquiry_id}/close")
    replied = admin.post(f"{BASE}/{enquiry_id}/reply", json={"body": "Following up."}).json()["data"]
    assert (replied["status"], replied["closed_at"]) == ("replied", None)


# What the person sent can't be changed, even by the centre's admins
# (only the status moves).
def test_what_was_sent_stays(api: Api, admin, unique_email):
    from sqlalchemy import text

    from app.db.session import SessionLocal

    enquiry_id = _enquiry_id(api, unique_email)
    [(admin_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = 't1user@test.com'")
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )

    with SessionLocal() as db:
        db.execute(
            text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
            {"u": admin_id, "l": location_id},
        )
        db.execute(text("UPDATE public.enquiries SET message = 'changed' WHERE id = :id"), {"id": enquiry_id})
        db.commit()

    [(_, _, message)] = _stored(api, unique_email)
    assert message == ENQUIRY["message"]


# The business's owner sets the centre's enquiries address with its details.
def test_owner_sets_the_enquiries_address(api: Api, owner):
    [location] = [l for l in owner.get("/business/v1/locations").json()["data"] if l["code"] == "location1"]
    body = {key: location[key] for key in ("name", "code", "address_line_1", "address_line_2", "suburb", "state", "postcode", "phone", "email", "timezone")}

    try:
        response = owner.put(f"/business/v1/locations/{location['id']}", json={**body, "enquiry_notice_email": "hello@centre.example.com"})

        assert response.status_code == 200, response.text
        assert response.json()["data"]["enquiry_notice_email"] == "hello@centre.example.com"
    finally:
        owner.put(f"/business/v1/locations/{location['id']}", json={**body, "enquiry_notice_email": None})
