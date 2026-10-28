import html
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.transaction import transactional
from app.errors.customer import EnquiryNotFoundError
from app.integrations.email.outbox import EmailOutbox
from app.integrations.email.renderer import RenderedEmail
from app.integrations.email.senders import OutgoingEmail
from app.platform.repositories.platform_enquiry import PlatformEnquiryRepository
from app.platform.schemas.enquiries import PlatformEnquiryResponse, SubmitPlatformEnquiryRequest


logger = logging.getLogger("app.platform")

PLATFORM_SENDER_NAME = "Session Pilot"

TOPIC_LABELS = {
    "own_business": "Using the software for their business",
    "build_software": "Having software like this built",
}


def _notice(enquiry_id: UUID, body: SubmitPlatformEnquiryRequest) -> OutgoingEmail:
    """
    The enquiry in full, to the platform's contact address, with Reply-To
    the person: replying in that mailbox answers them. An email to
    ourselves about a business enquiry, so not a family email
    (docs/email-policy.md doesn't apply).
    """
    lines = [
        ("Topic", TOPIC_LABELS[body.topic]),
        ("Name", body.name),
        ("Email", str(body.email)),
        ("Phone", body.phone or "-"),
        ("Business", body.business_name or "-"),
    ]

    text = "\n".join(f"{label}: {value}" for label, value in lines) + f"\n\n{body.message}\n\nReply to this email to answer them.\nReference: {enquiry_id}"
    rows = "".join(
        f"<tr><td style=\"padding:4px 12px 4px 0;color:#71717a;\">{html.escape(label)}</td><td style=\"padding:4px 0;\"><strong>{html.escape(value)}</strong></td></tr>"
        for label, value in lines
    )
    body_html = (
        f"<table>{rows}</table>"
        f"<p style=\"white-space:pre-line;margin:16px 0;padding:16px;background:#f4f4f5;\">{html.escape(body.message)}</p>"
        f"<p style=\"color:#71717a;\">Reply to this email to answer them.</p>"
    )

    return OutgoingEmail(
        to_email=settings.PLATFORM_CONTACT_EMAIL,
        from_name=PLATFORM_SENDER_NAME,
        reply_to=str(body.email),
        rendered=RenderedEmail(
            subject=f"New enquiry: {TOPIC_LABELS[body.topic]}",
            html=body_html,
            text=text,
        ),
        requires_tls=False,
        tenant_name="platform",
        tags={"email_type": "platform_enquiry"},
    )


class PlatformEnquiryService:
    """
    The platform's contact page (docs/platform-site.md). Anyone sends an
    enquiry; it's kept for the platform console, and emailed in full to the
    platform's contact address (PLATFORM_CONTACT_EMAIL) after it's saved,
    to be answered from that mailbox. The platform's admins mark them done.
    """

    def __init__(
        self,
        *,
        db: Session,
        enquiry_repository: PlatformEnquiryRepository,
    ):
        self.db = db
        self.enquiry_repository = enquiry_repository
        self.emails = EmailOutbox(db)

    @transactional
    def submit(self, *, body: SubmitPlatformEnquiryRequest) -> None:
        # Only a bot fills in the hidden field: it's told it worked.
        if body.website:
            logger.info("Platform enquiry dropped: hidden field filled in", extra={"event": "platform_enquiry_spam", "result": "ignored", "reason": "-"})
            return

        enquiry_id = self.enquiry_repository.submit(
            name=body.name,
            email=str(body.email),
            phone=body.phone,
            business_name=body.business_name,
            topic=body.topic,
            message=body.message,
        )

        if settings.PLATFORM_CONTACT_EMAIL:
            self.emails.queue(_notice(enquiry_id, body))

        logger.info(
            "Platform enquiry received",
            extra={"event": "platform_enquiry_received", "result": "success", "reason": f"enquiry_id={enquiry_id}; topic={body.topic}"},
        )

    def list(self, *, closed: bool) -> list[PlatformEnquiryResponse]:
        return [
            PlatformEnquiryResponse.model_validate(row, from_attributes=True)
            for row in self.enquiry_repository.list(closed=closed)
        ]

    @transactional
    def set_closed(self, *, id: UUID, closed: bool) -> PlatformEnquiryResponse:
        row = self.enquiry_repository.set_closed(id=id, closed=closed)

        if not row:
            raise EnquiryNotFoundError()

        return PlatformEnquiryResponse.model_validate(row, from_attributes=True)
