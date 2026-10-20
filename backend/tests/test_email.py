"""
The email engine (app/integrations/email, docs/email-policy.md): every email
keeps to the content rules, tenant wording can't break out of its slots,
emails with a secret only go over TLS, and the email log holds who and
what happened, never the address or the body, and is private to the email
service (and readable by location admins).
"""

import dataclasses
import logging

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.db.models import EmailTypeEnum as EmailType
from app.db.session import SessionLocal
from app.integrations.email.catalogue import CATALOGUE
from app.integrations.email.client import EmailClient
from app.integrations.email.links import Links
from app.integrations.email.masking import mask_email
from app.integrations.email.messages import (
    MESSAGE_TYPES,
    PasswordChangedEmail,
    WelcomeEmail,
)
from app.integrations.email.outbox import EmailOutbox
from app.integrations.email.renderer import Centre, Override, render
from app.integrations.email.senders import LogSender, OutgoingEmail, SendResult, SesSender
from tests.factories import Api


CENTRE = Centre(name="Sunshine OSHC", email="hello@sunshine.test", phone="0400 000 000", primary_color="#0a7")

VALUES = {"first_name": "Jordan", "child_first_name": "Sam"}

# What each email's locked block needs, with recognisable values.
BLOCKS = {
    EmailType.PASSWORD_RESET: {"reset_url": "https://t.test/l/reset-password?token=TOKEN123"},
    EmailType.PASSWORD_CHANGED: {"login_url": "https://t.test/l/login"},
    EmailType.WELCOME: {"login_url": "https://t.test/l/login"},
    EmailType.BOOKING_CONFIRMATION: {"reference": "BK-1234", "total": "$60.00", "bookings_url": "https://t.test/l/bookings"},
    EmailType.REFUND_CONFIRMATION: {"reference": "RF-1234", "amount": "$30.00", "bookings_url": "https://t.test/l/bookings"},
    EmailType.DOCUMENTS_REQUESTED: {"child_url": "https://t.test/l/account/children/x?state=manage-documents"},
    EmailType.CHILD_APPROVED: {"book_url": "https://t.test/l/bookings/new"},
    EmailType.KIOSK_PIN: {"pin": "4821"},
}

# Never in an email (docs/email-policy.md, section 2).
HEALTH_WORDS = ("medical", "allergy", "allergies", "anaphylaxis", "asthma", "medication", "epipen", "diagnos")


def _render(email_type: EmailType, override: Override | None = None):
    return render(CATALOGUE[email_type], centre=CENTRE, values=VALUES, block=BLOCKS[email_type], override=override)


class RecordingSender:
    """Accepts every email and keeps it, like SES would."""

    def __init__(self, result: SendResult | None = None, error: Exception | None = None):
        self.sent: list[OutgoingEmail] = []
        self.result = result
        self.error = error

    def send(self, email: OutgoingEmail) -> SendResult:
        self.sent.append(email)

        if self.error:
            raise self.error

        return self.result or SendResult(message_id=f"ses-{len(self.sent)}-{id(self)}")


# ---------------------------------------------------------------------------
# Content rules
# ---------------------------------------------------------------------------

# No email names a person in its subject (subjects show on lock screens and
# stay in SES's records).
@pytest.mark.parametrize("email_type", list(EmailType))
def test_subjects_name_no_one(email_type):
    subject = _render(email_type).subject

    assert "Jordan" not in subject
    assert "Sam" not in subject


# No email uses a health word anywhere.
@pytest.mark.parametrize("email_type", list(EmailType))
def test_no_health_words(email_type):
    rendered = _render(email_type)

    for part in (rendered.subject, rendered.html, rendered.text):
        assert not any(word in part.lower() for word in HEALTH_WORDS), (email_type, part)


# No email message has a field for what must never be in an email (a
# surname, a date of birth, medical details, a staff member's message), so
# no service can put one in by mistake.
def test_messages_hold_no_never_tier_details():
    banned = {"last_name", "child_last_name", "dob", "medical_info", "allergy_info", "medication_info", "message", "documentation_request", "phone"}

    for message_type in MESSAGE_TYPES:
        fields = {field.name for field in dataclasses.fields(message_type)}
        assert not banned & fields, message_type.__name__


# Every email has its locked block and the centre's footer, in both the
# HTML and the plain text.
@pytest.mark.parametrize("email_type", list(EmailType))
def test_locked_block_and_footer_always_present(email_type):
    rendered = _render(email_type, Override(subject="Hi", heading="Hi", body="Just this.", sign_off="Bye"))
    key_value = next(iter(BLOCKS[email_type].values()))

    for part in (rendered.html, rendered.text):
        assert key_value in part
        assert "Sunshine OSHC" in part


# Only the reset and PIN emails carry a secret, and only they require TLS.
def test_only_emails_with_a_secret_require_tls():
    assert {t for t, d in CATALOGUE.items() if d.requires_tls} == {EmailType.PASSWORD_RESET, EmailType.KIOSK_PIN}


# ---------------------------------------------------------------------------
# Tenant wording
# ---------------------------------------------------------------------------

# A tenant's wording replaces only its own slots; the rest stay ours.
def test_override_replaces_only_its_slots():
    rendered = _render(EmailType.WELCOME, Override(body="Kia ora {first_name}, welcome to {centre_name}."))

    assert "Kia ora Jordan, welcome to Sunshine OSHC." in rendered.text
    assert rendered.subject == "Welcome to Sunshine OSHC"


# Tenant wording can't reach template logic or inject HTML: unknown
# placeholders stay as typed, Jinja syntax is just text, markup is escaped.
def test_override_cannot_break_out():
    rendered = _render(
        EmailType.CHILD_APPROVED,
        Override(body="{config} {{ config }} {% if 1 %}x{% endif %} <script>alert(1)</script> {child_first_name}"),
    )

    assert "{config}" in rendered.text
    assert "{{ config }}" in rendered.text
    assert "<script>" not in rendered.html
    assert "&lt;script&gt;" in rendered.html
    assert "Sam" in rendered.text


# A placeholder from another email can't be used (e.g. a child's name in an
# email that isn't about a child).
def test_override_uses_only_its_own_placeholders():
    rendered = _render(EmailType.WELCOME, Override(body="About {child_first_name}"))

    assert "About {child_first_name}" in rendered.text


# A blank tenant slot keeps our wording.
def test_blank_override_slot_keeps_the_default():
    rendered = _render(EmailType.PASSWORD_CHANGED, Override(subject="   "))

    assert rendered.subject == "Your password was changed"


# A brand colour that isn't a plain hex colour can't reach the styles.
def test_unsafe_brand_colour_is_ignored():
    centre = Centre(name="X", email=None, phone=None, primary_color="red;background:url(x)")
    rendered = render(CATALOGUE[EmailType.WELCOME], centre=centre, values=VALUES, block=BLOCKS[EmailType.WELCOME])

    assert "url(x)" not in rendered.html


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

class _FakeSes:
    def __init__(self):
        self.requests = []

    def send_email(self, **request):
        self.requests.append(request)
        return {"MessageId": "ses-message-1"}


def _outgoing(email_type: EmailType) -> OutgoingEmail:
    return OutgoingEmail(
        to_email="family@example.test",
        from_name="Sunshine OSHC",
        reply_to="hello@sunshine.test",
        rendered=_render(email_type),
        requires_tls=CATALOGUE[email_type].requires_tls,
        tenant_name="tenant1",
        tags={"tenant_id": "t", "location_id": "l", "email_type": email_type.value},
    )


def _ses(monkeypatch) -> tuple[SesSender, _FakeSes]:
    monkeypatch.setattr(settings, "SES_CONFIGURATION_SET", "standard")
    monkeypatch.setattr(settings, "SES_TLS_CONFIGURATION_SET", "tls-required")
    monkeypatch.setattr(settings, "SES_USE_TENANTS", True)

    sender = SesSender()
    fake = _FakeSes()
    sender._client = fake

    return sender, fake


# SES gets finished content as the centre, replying to the centre, under the
# tenant's SES tenant, tagged for usage; emails with a secret use the TLS
# configuration set and the rest don't.
def test_ses_request(monkeypatch):
    sender, fake = _ses(monkeypatch)

    assert sender.send(_outgoing(EmailType.PASSWORD_RESET)).message_id == "ses-message-1"
    sender.send(_outgoing(EmailType.WELCOME))

    reset, welcome = fake.requests

    assert reset["ConfigurationSetName"] == "tls-required"
    assert welcome["ConfigurationSetName"] == "standard"
    assert reset["FromEmailAddress"] == f"Sunshine OSHC <{settings.SES_FROM_ADDRESS}>"
    assert reset["ReplyToAddresses"] == ["hello@sunshine.test"]
    assert reset["TenantName"] == "tenant1"
    assert {tag["Name"] for tag in reset["EmailTags"]} == {"tenant_id", "location_id", "email_type"}
    assert set(reset["Content"]["Simple"]["Body"]) == {"Text", "Html"}


# Without its TLS configuration set, an email with a secret isn't sent at
# all rather than going without encryption.
def test_secret_email_not_sent_without_tls_configuration(monkeypatch):
    sender, fake = _ses(monkeypatch)
    monkeypatch.setattr(settings, "SES_TLS_CONFIGURATION_SET", None)

    result = sender.send(_outgoing(EmailType.KIOSK_PIN))

    assert result.error_code == "TlsConfigurationSetMissing"
    assert fake.requests == []


# The dev log shows the email's text (so links and PINs can be tried) only
# in dev; anywhere else, just the subject.
def test_log_sender_shows_body_only_in_dev(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="app.email")

    def logged() -> str:
        return " ".join(getattr(record, "reason", "") for record in caplog.records)

    monkeypatch.setattr(settings, "APP_ENV", "test")
    LogSender().send(_outgoing(EmailType.KIOSK_PIN))
    assert "Your kiosk PIN" in logged()
    assert "4821" not in logged()

    monkeypatch.setattr(settings, "APP_ENV", "dev")
    LogSender().send(_outgoing(EmailType.KIOSK_PIN))
    assert "4821" in logged()


# Links go to the tenant's custom domain when it has one, else the
# configured dev address, else the tenant's subdomain.
def test_links(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL_TEMPLATE", None)
    assert Links(tenant_code="t1", custom_domain=None, location_code="loc").url("login") == f"https://t1.{settings.BASE_DOMAIN}/loc/login"

    monkeypatch.setattr(settings, "FRONTEND_URL_TEMPLATE", "http://{tenant}.localhost:5173")
    assert Links(tenant_code="t1", custom_domain=None, location_code="loc").url("reset-password", token="a b") == "http://t1.localhost:5173/loc/reset-password?token=a+b"

    assert Links(tenant_code="t1", custom_domain="care.example.com", location_code="loc").url() == "https://care.example.com/loc"


# Addresses are masked to the first letter and the domain.
def test_mask_email():
    assert mask_email("Jakson.B@Gmail.com") == "J***@gmail.com"
    assert mask_email("not-an-address") == "***"


# ---------------------------------------------------------------------------
# The email log
# ---------------------------------------------------------------------------

def _ids(api: Api, email: str, location: str = "location1") -> tuple[str, str]:
    """A user's id and their location's id (by location code)."""
    [(user_id, location_id)] = api.sql(
        "SELECT u.id::text, l.id::text FROM auth.users u "
        "JOIN auth.location_user_roles lur ON lur.user_id = u.id "
        "JOIN tenancy.locations l ON l.id = lur.location_id "
        "WHERE u.email = :email AND l.code = :location",
        email=email,
        location=location,
    )

    return user_id, location_id


def _row(api: Api, message_id) -> dict:
    [row] = api.sql("SELECT * FROM public.email_messages WHERE id = :id", id=str(message_id))

    return dict(row._mapping)


# A sent email leaves one row: who (by id and masked address), which email,
# sent, with the provider's message id. Never the full address or the body.
def test_send_is_logged_without_address_or_body(api: Api, customer):
    user_id, location_id = _ids(api, customer.email)
    sender = RecordingSender()

    message_id = EmailClient(sender=sender).send(WelcomeEmail(
        location_id=location_id, user_id=user_id, to_email=customer.email, first_name="Test",
    ))

    row = _row(api, message_id)
    assert row["status"] == "sent"
    assert row["email_type"] == "welcome"
    assert str(row["recipient_user_id"]) == user_id
    assert row["recipient_masked"] == mask_email(customer.email)
    assert row["provider_message_id"].startswith("ses-")
    assert row["tenant_id"] is not None

    stored = " ".join(str(value) for value in row.values())
    assert customer.email not in stored
    assert "Welcome" not in stored

    [email] = sender.sent
    assert email.to_email == customer.email
    assert email.from_name


# A provider refusal or an error while sending marks the row failed with a
# code, and never raises into the action that sent it.
@pytest.mark.parametrize(
    "sender, code",
    [
        (RecordingSender(result=SendResult(error_code="MessageRejected")), "MessageRejected"),
        (RecordingSender(error=ConnectionError("boom: someone@example.test")), "ConnectionError"),
    ],
)
def test_failed_send_is_logged_and_not_raised(api: Api, customer, sender, code):
    user_id, location_id = _ids(api, customer.email)

    message_id = EmailClient(sender=sender).send(PasswordChangedEmail(
        location_id=location_id, user_id=user_id, to_email=customer.email, first_name="Test",
    ))

    row = _row(api, message_id)
    assert row["status"] == "failed"
    assert row["error_code"] == code
    assert row["provider_message_id"] is None


# A tenant's own wording is used when it has some.
def test_tenant_override_is_used(api: Api, customer):
    user_id, location_id = _ids(api, customer.email)
    api.sql(
        "INSERT INTO tenancy.email_template_overrides (tenant_id, email_type, body) "
        "SELECT tenant_id, 'password_changed', 'Custom wording for {first_name}.' FROM tenancy.locations WHERE id = :id "
        "ON CONFLICT (tenant_id, email_type) DO UPDATE SET body = EXCLUDED.body",
        id=location_id,
    )

    try:
        sender = RecordingSender()
        EmailClient(sender=sender).send(PasswordChangedEmail(
            location_id=location_id, user_id=user_id, to_email=customer.email, first_name="Robin",
        ))

        assert "Custom wording for Robin." in sender.sent[0].rendered.text
    finally:
        # Shared row: put it back.
        api.sql(
            "DELETE FROM tenancy.email_template_overrides WHERE email_type = 'password_changed' "
            "AND tenant_id = (SELECT tenant_id FROM tenancy.locations WHERE id = :id)",
            id=location_id,
        )


def _session_as(user_id: str, location_id: str):
    db = SessionLocal()
    db.execute(text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"), {"u": user_id, "l": location_id})

    return db


# Request sessions can't touch the log: a family sees none of it (even
# their own) and can't write to it; only the email service can.
def test_log_is_private_to_the_email_service(api: Api, customer):
    user_id, location_id = _ids(api, customer.email)
    EmailClient(sender=RecordingSender()).send(WelcomeEmail(
        location_id=location_id, user_id=user_id, to_email=customer.email, first_name="Test",
    ))

    with _session_as(user_id, location_id) as db:
        assert db.execute(text("SELECT count(*) FROM public.email_messages")).scalar_one() == 0

        with pytest.raises(Exception):
            db.execute(
                text("INSERT INTO public.email_messages (tenant_id, location_id, email_type) "
                     "SELECT tenant_id, id, 'welcome' FROM tenancy.locations WHERE id = :l"),
                {"l": location_id},
            )


# A location admin can read their location's log; another tenant's admin
# can't.
def test_location_admin_reads_their_log(api: Api, customer):
    user_id, location_id = _ids(api, customer.email)
    message_id = EmailClient(sender=RecordingSender()).send(WelcomeEmail(
        location_id=location_id, user_id=user_id, to_email=customer.email, first_name="Test",
    ))

    admin_id, admin_location = _ids(api, "t1user@test.com")
    other_admin_id, other_location = _ids(api, "t2user@test.com", "location2")

    with _session_as(admin_id, admin_location) as db:
        assert db.execute(text("SELECT count(*) FROM public.email_messages WHERE id = :id"), {"id": str(message_id)}).scalar_one() == 1

    with _session_as(other_admin_id, other_location) as db:
        assert db.execute(text("SELECT count(*) FROM public.email_messages WHERE id = :id"), {"id": str(message_id)}).scalar_one() == 0


# The app's own database role can't read the cross-tenant usage report.
def test_usage_report_is_not_readable_by_the_app():
    with SessionLocal() as db, pytest.raises(Exception):
        db.execute(text("SELECT * FROM reporting.email_usage_monthly")).all()


# ---------------------------------------------------------------------------
# The outbox: emails wait for their transaction
# ---------------------------------------------------------------------------

def _welcome(location_id: str) -> WelcomeEmail:
    return WelcomeEmail(location_id=location_id, user_id=location_id, to_email="a@example.test", first_name="A")


# A queued email is sent once its transaction commits, and not before.
def test_queued_email_is_sent_on_commit(api: Api, sent_emails):
    _, location_id = _ids(api, "t1user@test.com")

    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        EmailOutbox(db).queue(_welcome(location_id))

        assert sent_emails() == []

        db.commit()

    assert sent_emails() == [_welcome(location_id)]


# A rolled-back transaction drops its queued emails: nobody hears about a
# change that didn't happen, even if the session commits something later.
def test_queued_email_is_dropped_on_rollback(api: Api, sent_emails):
    _, location_id = _ids(api, "t1user@test.com")

    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        EmailOutbox(db).queue(_welcome(location_id))
        db.rollback()

        db.execute(text("SELECT 1"))
        db.commit()

    assert sent_emails() == []
