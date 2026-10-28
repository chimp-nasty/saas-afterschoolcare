from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, StringConstraints, field_validator


PlatformEnquiryTopic = Literal["own_business", "build_software"]


class SubmitPlatformEnquiryRequest(BaseModel):
    """The platform's contact page (docs/platform-site.md). Anyone can send one."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    email: EmailStr
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    business_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    topic: PlatformEnquiryTopic
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]
    # A field people can't see: only bots fill it in. Accepted (so they
    # don't learn) but not kept.
    website: str | None = None

    @field_validator("phone", "business_name")
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value or None


class PlatformEnquiryResponse(BaseModel):
    """An enquiry in the platform console."""

    id: UUID
    name: str
    email: str
    phone: str | None
    business_name: str | None
    topic: PlatformEnquiryTopic
    message: str
    created_at: datetime
    closed_at: datetime | None
