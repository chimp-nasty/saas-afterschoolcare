"""
Every email the platform sends, and what each may contain. The code side of
docs/email-policy.md (section 3): add an email there first, then here.

Each email has editable slots (subject, heading, body, sign-off) with our
default wording; a tenant may replace any slot with their own wording
(tenancy.email_template_overrides), using only that email's placeholders,
written {like_this}. The locked block (templates/blocks/<type>.html and
.txt: links, the PIN, amounts) and the footer can't be changed.

Content rules (enforced by tests/test_email_rendering.py): subjects have no
names; a child is named by first name only, in the body; no health words;
nothing a family wrote or staff typed.
"""

from dataclasses import dataclass

from app.db.models import EmailTypeEnum as EmailType


# Every email can use these.
_COMMON = frozenset({"first_name", "centre_name"})


@dataclass(frozen=True)
class EmailDefinition:
    type: EmailType

    # Placeholders tenant wording may use (on top of first_name and
    # centre_name).
    placeholders: frozenset[str]

    subject: str
    heading: str
    body: str
    sign_off: str

    # Why the recipient gets it (the footer).
    footer_reason: str

    # Carries a secret (a reset link or PIN): sent only over an encrypted
    # connection (SES_TLS_CONFIGURATION_SET).
    requires_tls: bool = False

    @property
    def allowed_placeholders(self) -> frozenset[str]:
        return _COMMON | self.placeholders


_ACCOUNT_HOLDER = "You're receiving this because you have an account with {centre_name}."
_SIGN_OFF = "The {centre_name} team"


CATALOGUE: dict[EmailType, EmailDefinition] = {
    definition.type: definition
    for definition in (
        EmailDefinition(
            type=EmailType.PASSWORD_RESET,
            placeholders=frozenset(),
            subject="Reset your password",
            heading="Reset your password",
            body=(
                "Hi {first_name},\n\n"
                "We received a request to reset the password for your {centre_name} account."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
            requires_tls=True,
        ),
        EmailDefinition(
            type=EmailType.PASSWORD_CHANGED,
            placeholders=frozenset(),
            subject="Your password was changed",
            heading="Your password was changed",
            body=(
                "Hi {first_name},\n\n"
                "The password for your {centre_name} account has just been changed."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
        ),
        EmailDefinition(
            type=EmailType.WELCOME,
            placeholders=frozenset(),
            subject="Welcome to {centre_name}",
            heading="Welcome to {centre_name}",
            body=(
                "Hi {first_name},\n\n"
                "Your account is ready. Next, add your children and the people who can "
                "collect them, then book your first sessions."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
        ),
        EmailDefinition(
            type=EmailType.BOOKING_CONFIRMATION,
            placeholders=frozenset(),
            subject="Your booking is confirmed",
            heading="Your booking is confirmed",
            body=(
                "Hi {first_name},\n\n"
                "Your booking at {centre_name} is confirmed. You can see the sessions "
                "you've booked in your account."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
        ),
        EmailDefinition(
            type=EmailType.REFUND_CONFIRMATION,
            placeholders=frozenset(),
            subject="Your refund has been processed",
            heading="Your refund has been processed",
            body=(
                "Hi {first_name},\n\n"
                "Your refund from {centre_name} has been processed. It can take 5 to 10 "
                "business days to appear on your statement."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
        ),
        EmailDefinition(
            type=EmailType.DOCUMENTS_REQUESTED,
            placeholders=frozenset({"child_first_name"}),
            subject="Action needed in your account",
            heading="Documents needed",
            body=(
                "Hi {first_name},\n\n"
                "{centre_name} has asked for documents for {child_first_name}. Log in to "
                "see what's needed and upload them. {child_first_name} can't be booked "
                "until the centre has reviewed them."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
        ),
        EmailDefinition(
            type=EmailType.CHILD_APPROVED,
            placeholders=frozenset({"child_first_name"}),
            subject="Your child's profile has been approved",
            heading="Profile approved",
            body=(
                "Hi {first_name},\n\n"
                "{centre_name} has approved {child_first_name}'s profile. You can now book "
                "sessions for {child_first_name}."
            ),
            sign_off=_SIGN_OFF,
            footer_reason=_ACCOUNT_HOLDER,
        ),
        EmailDefinition(
            type=EmailType.KIOSK_PIN,
            placeholders=frozenset(),
            subject="Your kiosk PIN",
            heading="Your kiosk PIN",
            body=(
                "Hi {first_name},\n\n"
                "Here is your PIN for the sign-in kiosk at {centre_name}. You'll choose "
                "your own PIN the first time you use the kiosk."
            ),
            sign_off=_SIGN_OFF,
            footer_reason="You're receiving this because you've been added as a pickup person at {centre_name}.",
            requires_tls=True,
        ),
    )
}

assert set(CATALOGUE) == set(EmailType), "every email type needs a definition"
