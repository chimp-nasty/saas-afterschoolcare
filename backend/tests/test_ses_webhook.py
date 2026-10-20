"""
The SES webhook (app/integrations/email/webhook.py): SNS posts bounce,
complaint and delivery events, and each updates its email's status in the
log. Only genuine, current messages from our topic are accepted; a status
only moves forward.

Messages are signed here with a throwaway key and certificate, standing in
for SNS's (the certificate fetch is patched), so nothing goes to AWS.
"""

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from app.core.config import settings
from app.integrations.email.client import EmailClient
from app.integrations.email.messages import WelcomeEmail
from app.integrations.email.senders import SendResult
from tests.factories import Api


TOPIC = "arn:aws:sns:ap-southeast-2:123456789012:ses-events"
CERT_URL = "https://sns.ap-southeast-2.amazonaws.com/SimpleNotificationService-test.pem"


def _certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sns.amazonaws.com")])
    now = datetime.now(timezone.utc)

    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )

    return key, certificate.public_bytes(serialization.Encoding.PEM)


KEY, CERT_PEM = _certificate()

_SIGNED = {
    "Notification": ("Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"),
    "SubscriptionConfirmation": ("Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"),
}


def _signed(message_type: str, *, sent_at: datetime | None = None, cert_url: str = CERT_URL, topic: str = TOPIC, **fields) -> dict:
    """An SNS message signed the way SNS signs (signature version 2)."""
    message = {
        "Type": message_type,
        "MessageId": str(uuid.uuid4()),
        "TopicArn": topic,
        "Timestamp": (sent_at or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "SignatureVersion": "2",
        "SigningCertURL": cert_url,
        **fields,
    }

    string_to_sign = "".join(
        f"{field}\n{message[field]}\n" for field in _SIGNED[message_type] if field in message
    ).encode()

    message["Signature"] = base64.b64encode(
        KEY.sign(string_to_sign, padding.PKCS1v15(), hashes.SHA256())
    ).decode()

    return message


def _event(kind: str, provider_message_id: str, **extra) -> dict:
    """An SNS notification carrying one SES event (as event publishing sends it)."""
    event = {"eventType": kind, "mail": {"messageId": provider_message_id, "destination": ["someone@example.test"]}, **extra}

    return _signed("Notification", Message=json.dumps(event))


@pytest.fixture(autouse=True)
def sns(monkeypatch):
    monkeypatch.setattr(settings, "SES_EVENTS_TOPIC_ARN", TOPIC)
    monkeypatch.setattr("app.integrations.email.sns.fetch_certificate", lambda url: CERT_PEM)


def _post(api: Api, message: dict):
    return api.client().post("/api/v1/webhooks/ses", content=json.dumps(message))


class _Accepting:
    """A sender SES accepted the email from, with a known message id."""

    def __init__(self):
        self.message_id = f"ses-{uuid.uuid4()}"

    def send(self, email):
        return SendResult(message_id=self.message_id)


def _sent_email(api: Api, customer) -> tuple[str, str]:
    """A logged, sent email: returns (its log row id, the SES message id)."""
    [(user_id, location_id)] = api.sql(
        "SELECT u.id::text, lur.location_id::text FROM auth.users u "
        "JOIN auth.location_user_roles lur ON lur.user_id = u.id WHERE u.email = :email",
        email=customer.email,
    )
    sender = _Accepting()

    row_id = EmailClient(sender=sender).send(WelcomeEmail(
        location_id=location_id, user_id=user_id, to_email=customer.email, first_name="Test",
    ))

    return str(row_id), sender.message_id


def _status(api: Api, row_id: str) -> str:
    [(status,)] = api.sql("SELECT status::text FROM public.email_messages WHERE id = :id", id=row_id)

    return status


# ---------------------------------------------------------------------------
# Events update the log
# ---------------------------------------------------------------------------

# A delivery marks the email delivered.
def test_delivery_is_recorded(api: Api, customer):
    row_id, provider_id = _sent_email(api, customer)

    assert _post(api, _event("Delivery", provider_id)).status_code == 200

    assert _status(api, row_id) == "delivered"


# A hard bounce marks it bounced, and a later delivery report doesn't undo it.
def test_bounce_is_recorded_and_kept(api: Api, customer):
    row_id, provider_id = _sent_email(api, customer)

    _post(api, _event("Bounce", provider_id, bounce={"bounceType": "Permanent"}))
    _post(api, _event("Delivery", provider_id))

    assert _status(api, row_id) == "bounced"


# A soft bounce may still be delivered, so it changes nothing.
def test_transient_bounce_is_ignored(api: Api, customer):
    row_id, provider_id = _sent_email(api, customer)

    _post(api, _event("Bounce", provider_id, bounce={"bounceType": "Transient"}))

    assert _status(api, row_id) == "sent"


# A complaint after delivery marks it complained.
def test_complaint_after_delivery(api: Api, customer):
    row_id, provider_id = _sent_email(api, customer)

    _post(api, _event("Delivery", provider_id))
    _post(api, _event("Complaint", provider_id))

    assert _status(api, row_id) == "complained"


# An event for an email we don't know (e.g. another app on the account) is
# acknowledged and ignored, so SNS doesn't keep retrying it.
def test_unknown_email_is_ignored(api: Api):
    assert _post(api, _event("Delivery", "not-one-of-ours")).status_code == 200


# ---------------------------------------------------------------------------
# Only genuine, current messages from our topic
# ---------------------------------------------------------------------------

# A message changed after signing is refused and changes nothing.
def test_tampered_message_is_refused(api: Api, customer):
    row_id, provider_id = _sent_email(api, customer)
    message = _event("Delivery", "someone-else")
    message["Message"] = json.dumps({"eventType": "Complaint", "mail": {"messageId": provider_id}})

    assert _post(api, message).status_code == 400
    assert _status(api, row_id) == "sent"


# Another topic's messages are refused, even when properly signed.
def test_other_topic_is_refused(api: Api, customer):
    _, provider_id = _sent_email(api, customer)
    message = _signed("Notification", topic="arn:aws:sns:ap-southeast-2:999:other", Message=json.dumps({"eventType": "Delivery", "mail": {"messageId": provider_id}}))

    assert _post(api, message).status_code == 400


# A signing certificate that isn't on an SNS host is never trusted.
def test_certificate_must_come_from_sns(api: Api):
    message = _signed("Notification", cert_url="https://evil.example.com/cert.pem", Message="{}")

    assert _post(api, message).status_code == 400


# An old message (a replay) is refused.
def test_old_message_is_refused(api: Api):
    message = _signed("Notification", sent_at=datetime.now(timezone.utc) - timedelta(hours=2), Message="{}")

    assert _post(api, message).status_code == 400


# Until the topic is configured, nothing is accepted.
def test_nothing_accepted_without_a_topic(api: Api, monkeypatch):
    monkeypatch.setattr(settings, "SES_EVENTS_TOPIC_ARN", None)

    assert _post(api, _event("Delivery", "x")).status_code == 400


# A body that isn't JSON is refused.
def test_garbage_is_refused(api: Api):
    assert api.client().post("/api/v1/webhooks/ses", content=b"not json").status_code == 400


# ---------------------------------------------------------------------------
# Subscribing
# ---------------------------------------------------------------------------

# Our topic's subscription is confirmed by visiting its SNS link.
def test_subscription_is_confirmed(api: Api, monkeypatch):
    visited = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "app.integrations.email.webhook.urllib.request.urlopen",
        lambda url, timeout: visited.append(url) or _Response(),
    )
    url = "https://sns.ap-southeast-2.amazonaws.com/?Action=ConfirmSubscription&Token=abc"

    response = _post(api, _signed("SubscriptionConfirmation", Message="confirm", SubscribeURL=url, Token="abc"))

    assert response.status_code == 200
    assert visited == [url]


# A confirmation link that isn't SNS's is never visited.
def test_subscription_link_must_be_sns(api: Api, monkeypatch):
    visited = []
    monkeypatch.setattr(
        "app.integrations.email.webhook.urllib.request.urlopen",
        lambda url, timeout: visited.append(url),
    )

    response = _post(api, _signed("SubscriptionConfirmation", Message="confirm", SubscribeURL="https://evil.example.com/x", Token="abc"))

    assert response.status_code == 400
    assert visited == []
