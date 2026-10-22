"""
One message class per email in the catalogue: everything that one email to
one person needs, and nothing else. Services build these and queue them
(EmailOutbox); EmailClient.send(message) turns one into a logged, rendered
email.

The fields are the policy (docs/email-policy.md, section 2): no message has
a field for a surname, a date of birth, medical details or a staff
member's message, so none can reach an email. Adding a field here is
adding content to an email: check it against the policy first.
"""

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.db.models import EmailTypeEnum as EmailType
from app.integrations.email.links import Links


@dataclass(frozen=True, kw_only=True)
class EmailMessage:
    email_type: ClassVar[EmailType]

    # The centre it's sent as (name, reply-to, links).
    location_id: UUID
    to_email: str
    first_name: str

    def recipient(self) -> dict[str, UUID]:
        """Who the email log records it against."""
        return {"recipient_user_id": self.user_id}

    def values(self) -> dict[str, str]:
        """The placeholders its wording may use."""
        return {"first_name": self.first_name}

    def block(self, links: Links) -> dict:
        """What its locked block shows."""
        return {}


@dataclass(frozen=True, kw_only=True)
class PasswordResetEmail(EmailMessage):
    email_type = EmailType.PASSWORD_RESET

    user_id: UUID
    token: str

    def block(self, links):
        return {"reset_url": links.url("reset-password", token=self.token)}


@dataclass(frozen=True, kw_only=True)
class StaffInviteEmail(EmailMessage):
    """Someone added to a centre's staff: a link to set their password."""

    email_type = EmailType.STAFF_INVITE

    user_id: UUID
    token: str

    def block(self, links):
        return {"invite_url": links.url("reset-password", token=self.token, invite="1")}


@dataclass(frozen=True, kw_only=True)
class PasswordChangedEmail(EmailMessage):
    email_type = EmailType.PASSWORD_CHANGED

    user_id: UUID

    def block(self, links):
        return {"login_url": links.url("login")}


@dataclass(frozen=True, kw_only=True)
class WelcomeEmail(EmailMessage):
    email_type = EmailType.WELCOME

    user_id: UUID

    def block(self, links):
        return {"login_url": links.url("login")}


@dataclass(frozen=True, kw_only=True)
class BookingConfirmationEmail(EmailMessage):
    email_type = EmailType.BOOKING_CONFIRMATION

    user_id: UUID
    reference: str
    total_cents: int
    currency: str

    def block(self, links):
        return {
            "reference": self.reference,
            "total": format_amount(self.total_cents, self.currency),
            "bookings_url": links.url("bookings"),
        }


@dataclass(frozen=True, kw_only=True)
class RefundConfirmationEmail(EmailMessage):
    email_type = EmailType.REFUND_CONFIRMATION

    user_id: UUID
    reference: str
    amount_cents: int
    currency: str

    def block(self, links):
        return {
            "reference": self.reference,
            "amount": format_amount(self.amount_cents, self.currency),
            "bookings_url": links.url("bookings"),
        }


@dataclass(frozen=True, kw_only=True)
class DocumentsRequestedEmail(EmailMessage):
    """The staff member's message stays in the app: it often names a condition."""

    email_type = EmailType.DOCUMENTS_REQUESTED

    user_id: UUID
    child_id: UUID
    child_first_name: str

    def values(self):
        return {"first_name": self.first_name, "child_first_name": self.child_first_name}

    def block(self, links):
        return {"child_url": links.url(f"account/children/{self.child_id}", state="manage-documents")}


@dataclass(frozen=True, kw_only=True)
class NewMessageEmail(EmailMessage):
    """A message from the centre (slice 4-5): only that there is one. Its
    title and text stay in the app, as does which child it's about."""

    email_type = EmailType.NEW_MESSAGE

    user_id: UUID

    def values(self):
        return {"first_name": self.first_name}

    def block(self, links):
        return {"messages_url": links.url("actions")}


@dataclass(frozen=True, kw_only=True)
class ChildApprovedEmail(EmailMessage):
    email_type = EmailType.CHILD_APPROVED

    user_id: UUID
    child_first_name: str

    def values(self):
        return {"first_name": self.first_name, "child_first_name": self.child_first_name}

    def block(self, links):
        return {"book_url": links.url("bookings/new")}


@dataclass(frozen=True, kw_only=True)
class KioskPinEmail(EmailMessage):
    """A one-time setup PIN (docs/email-policy.md, section 4). Held only in
    memory until sent; never logged outside dev."""

    email_type = EmailType.KIOSK_PIN

    pickup_person_id: UUID
    pin: str

    def recipient(self):
        return {"recipient_pickup_person_id": self.pickup_person_id}

    def block(self, links):
        return {"pin": self.pin}


def short_reference(prefix: str, id: UUID) -> str:
    """"BK-3F9A21C0": a short code a family can quote to the centre."""
    return f"{prefix}-{str(id)[:8].upper()}"


def format_amount(cents: int, currency: str) -> str:
    """"$30.00", or "$30.00 NZD" for anything but Australian dollars."""
    code = getattr(currency, "value", currency)
    amount = f"${cents / 100:,.2f}"

    return amount if code == "AUD" else f"{amount} {code}"


MESSAGE_TYPES: tuple[type[EmailMessage], ...] = (
    PasswordResetEmail,
    PasswordChangedEmail,
    WelcomeEmail,
    BookingConfirmationEmail,
    RefundConfirmationEmail,
    DocumentsRequestedEmail,
    ChildApprovedEmail,
    NewMessageEmail,
    KioskPinEmail,
    StaffInviteEmail,
)

assert {m.email_type for m in MESSAGE_TYPES} == set(EmailType), "every email type needs a message"
