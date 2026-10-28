from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, StringConstraints, field_validator


EnquiryTopic = Literal["enrolment", "bookings", "general"]
EnquiryStatus = Literal["new", "replied", "closed"]

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]


class SubmitEnquiryRequest(BaseModel):
    """The centre page's contact form (docs/enquiries.md). Anyone can send one."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    email: EmailStr
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    topic: EnquiryTopic
    message: Text
    # A field people can't see: only bots fill it in. A filled-in form is
    # accepted (so they don't learn) but not kept.
    website: str | None = None

    @field_validator("phone")
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value or None


class EnquiryReplyRequest(BaseModel):
    body: Text


class EnquirySummaryResponse(BaseModel):
    """An enquiry in the admins' inbox."""

    id: UUID
    name: str
    email: str
    phone: str | None
    topic: EnquiryTopic
    status: EnquiryStatus
    # The start of the message, for the list.
    preview: str
    created_at: datetime
    replied_at: datetime | None


class EnquiryReplyResponse(BaseModel):
    id: UUID
    body: str
    created_at: datetime
    # Who replied (None once their account is gone).
    staff_name: str | None


class EnquiryResponse(BaseModel):
    """An enquiry with what was sent and every reply, oldest first."""

    id: UUID
    name: str
    email: str
    phone: str | None
    topic: EnquiryTopic
    status: EnquiryStatus
    message: str
    created_at: datetime
    replied_at: datetime | None
    closed_at: datetime | None
    replies: list[EnquiryReplyResponse]
