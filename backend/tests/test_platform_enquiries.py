"""
Enquiries to the platform itself (docs/platform-site.md): anyone sends one
from the platform's contact page, about using the software for their
business or having software like it built. It's kept for the platform
console, and emailed in full to the platform's contact address with
Reply-To the person. Only the platform's admins see them.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.email.senders import OutgoingEmail
from app.main import app
from tests.factories import Api


BASE = "/platform-enquiries/v1/"
PLATFORM_HOST = settings.BASE_DOMAIN

ENQUIRY = {
    "name": "Casey Morgan",
    "phone": "0412 000 111",
    "business_name": "Sunrise OSHC",
    "topic": "own_business",
    "message": "We run two centres and would like a demo.",
}


def _client(host: str = PLATFORM_HOST) -> TestClient:
    return TestClient(
        app,
        base_url=f"https://{host}/api",
        headers={
            "Origin": f"https://{host}",
            "X-Forwarded-For": f"10.251.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        },
    )


@pytest.fixture
def platform() -> TestClient:
    client = _client()
    response = client.post("/platform/v1/login", json={"email": "platform@test.com", "password": "123"})
    assert response.status_code == 200, response.text

    return client


@pytest.fixture
def email() -> str:
    return f"enquirer-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def contact_address(monkeypatch):
    monkeypatch.setattr(settings, "PLATFORM_CONTACT_EMAIL", "hello@sessionpilot.test")
    return "hello@sessionpilot.test"


def _stored(api: Api, email: str) -> list[tuple]:
    return api.sql(
        "SELECT topic::text, business_name, closed_at FROM public.platform_enquiries WHERE email = :e",
        e=email,
    )


# Anyone can send one from the platform's contact page, without logging in.
# It's kept, and emailed in full to the platform's contact address with
# Reply-To the person, so replying in that mailbox answers them.
def test_anyone_sends_one(api: Api, email, contact_address, sent_emails):
    response = _client().post(BASE, json={**ENQUIRY, "email": email})

    assert response.status_code == 201, response.text
    assert _stored(api, email) == [("own_business", "Sunrise OSHC", None)]

    [notice] = sent_emails(OutgoingEmail)
    assert notice.to_email == contact_address
    assert notice.reply_to == email
    assert ENQUIRY["message"] in notice.rendered.text
    assert "Sunrise OSHC" in notice.rendered.text


# With no contact address set, it's kept for the console and nobody is
# emailed.
def test_no_contact_address_no_email(api: Api, email, monkeypatch, sent_emails):
    monkeypatch.setattr(settings, "PLATFORM_CONTACT_EMAIL", None)

    assert _client().post(BASE, json={**ENQUIRY, "email": email}).status_code == 201
    assert len(_stored(api, email)) == 1
    assert sent_emails(OutgoingEmail) == []


# The hidden field is only filled in by bots: told it worked, nothing kept.
def test_the_spam_trap(api: Api, email, contact_address, sent_emails):
    response = _client().post(BASE, json={**ENQUIRY, "email": email, "website": "http://spam.example.com"})

    assert response.status_code == 201
    assert _stored(api, email) == []
    assert sent_emails(OutgoingEmail) == []


# A name, a valid email, one of the two topics and a message are needed.
@pytest.mark.parametrize(
    "changes",
    [{"name": ""}, {"email": "nope"}, {"topic": "other"}, {"message": ""}],
)
def test_what_one_needs(email, changes):
    assert _client().post(BASE, json={**ENQUIRY, "email": email, **changes}).status_code == 422


# It's the platform's: a business's site doesn't take them (404).
def test_not_on_a_business_site(email):
    response = _client(f"tenant1.{settings.BASE_DOMAIN}").post(BASE, json={**ENQUIRY, "email": email})

    assert response.status_code == 404


# The platform's admins see open enquiries, close one (it moves to the
# closed list) and reopen it.
def test_platform_admins_read_and_close(api: Api, platform, email):
    assert _client().post(BASE, json={**ENQUIRY, "email": email}).status_code == 201

    open_ = platform.get(BASE).json()["data"]
    [enquiry] = [e for e in open_ if e["email"] == email]
    assert enquiry["topic"] == "own_business"

    closed = platform.post(f"{BASE}{enquiry['id']}/close").json()["data"]
    assert closed["closed_at"] is not None
    assert email not in [e["email"] for e in platform.get(BASE).json()["data"]]
    assert email in [e["email"] for e in platform.get(BASE, params={"closed": "true"}).json()["data"]]

    reopened = platform.post(f"{BASE}{enquiry['id']}/reopen").json()["data"]
    assert reopened["closed_at"] is None


# Nobody else sees them: no platform login is refused (401).
def test_only_platform_admins_see_them():
    assert _client().get(BASE).status_code == 401
