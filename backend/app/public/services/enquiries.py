import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.customer import EnquiryNotFoundError
from app.integrations.email.messages import (
    EnquiryNoticeEmail,
    EnquiryReceivedEmail,
    EnquiryReplyEmail,
)
from app.integrations.email.outbox import EmailOutbox
from app.public.repositories.enquiry import EnquiryRepository
from app.public.schemas.enquiries import (
    EnquiryReplyRequest,
    EnquiryReplyResponse,
    EnquiryResponse,
    EnquirySummaryResponse,
    SubmitEnquiryRequest,
)
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.enquiries")

# How the notice to the centre's enquiries address names the topic
# ("about enrolment").
_TOPIC_WORDS = {
    "enrolment": "enrolment",
    "bookings": "bookings",
    "general": "a general question",
}

# Which statuses each inbox filter shows: open is what still needs a look.
STATUS_FILTERS = {
    "open": ["new", "replied"],
    "new": ["new"],
    "replied": ["replied"],
    "closed": ["closed"],
    "all": ["new", "replied", "closed"],
}


def _first_name(name: str) -> str:
    return name.split()[0] if name.split() else name


class EnquiryService:
    """
    The centre's contact form (docs/enquiries.md). Anyone sends an enquiry
    from the centre's page; it's kept in the app, not emailed. They get a
    receipt by email, and the centre's optional enquiries address gets a
    notice (who and what about, never the message). The centre's admins
    read, reply to (emailed to the person) and close enquiries; RLS limits
    them to their centre's.
    """

    def __init__(
        self,
        *,
        db: Session,
        enquiry_repository: EnquiryRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.enquiry_repository = enquiry_repository
        self.location_repository = location_repository
        self.emails = EmailOutbox(db)

    @transactional
    def submit(
        self,
        *,
        location_id: UUID,
        body: SubmitEnquiryRequest,
    ) -> None:
        # Only a bot fills in the hidden field: it's told it worked.
        if body.website:
            logger.info(
                "Enquiry dropped: hidden field filled in",
                extra={"event": "enquiry_spam", "result": "ignored", "reason": f"location_id={location_id}"},
            )
            return

        enquiry_id = self.enquiry_repository.submit(
            location_id=location_id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            topic=body.topic,
            message=body.message,
        )

        first_name = _first_name(body.name)

        self.emails.queue(EnquiryReceivedEmail(
            location_id=location_id,
            to_email=body.email,
            first_name=first_name,
        ))

        location = self.location_repository.get_by_id(id=location_id)

        if location and location.enquiry_notice_email:
            self.emails.queue(EnquiryNoticeEmail(
                location_id=location_id,
                to_email=location.enquiry_notice_email,
                first_name=location.name,
                enquiry_id=enquiry_id,
                enquirer_first_name=first_name,
                topic=_TOPIC_WORDS[body.topic],
            ))

        logger.info(
            "Enquiry received",
            extra={"event": "enquiry_received", "result": "success", "reason": f"enquiry_id={enquiry_id}"},
        )

    def list(
        self,
        *,
        location_id: UUID,
        status: str,
    ) -> list[EnquirySummaryResponse]:
        return [
            EnquirySummaryResponse.model_validate(row, from_attributes=True)
            for row in self.enquiry_repository.list_for_location(
                location_id=location_id,
                statuses=STATUS_FILTERS[status],
            )
        ]

    def get(
        self,
        *,
        location_id: UUID,
        id: UUID,
    ) -> EnquiryResponse:
        row = self.enquiry_repository.get(id=id, location_id=location_id)

        if not row:
            raise EnquiryNotFoundError()

        return EnquiryResponse(
            **row._mapping,
            replies=[
                EnquiryReplyResponse.model_validate(reply, from_attributes=True)
                for reply in self.enquiry_repository.replies(enquiry_id=id)
            ],
        )

    @transactional
    def reply(
        self,
        *,
        location_id: UUID,
        id: UUID,
        body: EnquiryReplyRequest,
    ) -> EnquiryResponse:
        """Kept with the enquiry and emailed to the person, as the centre (replies go to its contact email)."""
        enquiry = self.enquiry_repository.get(id=id, location_id=location_id)

        if not enquiry:
            raise EnquiryNotFoundError()

        self.enquiry_repository.add_reply(enquiry_id=id, body=body.body)

        self.emails.queue(EnquiryReplyEmail(
            location_id=location_id,
            to_email=enquiry.email,
            first_name=_first_name(enquiry.name),
            reply=body.body,
        ))

        logger.info(
            "Enquiry replied to",
            extra={"event": "enquiry_replied", "result": "success", "reason": f"enquiry_id={id}"},
        )

        return self.get(location_id=location_id, id=id)

    @transactional
    def close(
        self,
        *,
        location_id: UUID,
        id: UUID,
    ) -> EnquiryResponse:
        """Dealt with: off the open list. Replying again reopens it."""
        return self._set_status(location_id=location_id, id=id, status="closed")

    @transactional
    def reopen(
        self,
        *,
        location_id: UUID,
        id: UUID,
    ) -> EnquiryResponse:
        """Back on the open list: replied if it ever was, else new."""
        enquiry = self.enquiry_repository.get(id=id, location_id=location_id)

        if not enquiry:
            raise EnquiryNotFoundError()

        return self._set_status(
            location_id=location_id,
            id=id,
            status="replied" if enquiry.replied_at else "new",
        )

    def _set_status(self, *, location_id: UUID, id: UUID, status: str) -> EnquiryResponse:
        if not self.enquiry_repository.get(id=id, location_id=location_id):
            raise EnquiryNotFoundError()

        self.enquiry_repository.set_status(id=id, status=status)

        return self.get(location_id=location_id, id=id)
