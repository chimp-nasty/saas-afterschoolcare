from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator


# The business's site (docs/tenant-administration.md, stage 5): its
# landing page's words, branding, FAQs and policy documents.

# What can be uploaded: the two images and the two policies.
SiteFileKind = Literal["logo", "icon", "privacy", "terms"]
DocumentKind = Literal["privacy", "terms"]
ImageKind = Literal["logo", "icon"]

Colour = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^#[0-9A-Fa-f]{6}$")]

# The icons a highlight can have (ck_tenant_highlights_icon).
HighlightIcon = Literal["shield", "community", "activities", "location", "homework", "food", "staff", "booking"]


class SiteRequest(BaseModel):
    """
    The hero's headline (tagline) and paragraph, and the business's colours
    (empty: the app's defaults).
    """

    tagline: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    hero_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    primary_color: Colour | None = None
    secondary_color: Colour | None = None
    accent_color: Colour | None = None

    @field_validator("tagline", "hero_text", "primary_color", "secondary_color", "accent_color", mode="before")
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value or None


class SiteDocumentResponse(BaseModel):
    kind: DocumentKind
    uploaded_at: datetime


class FaqItem(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class HighlightItem(BaseModel):
    icon: HighlightIcon
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class HighlightsRequest(BaseModel):
    """The whole list, in order (at most 4: ck_tenant_highlights_limit)."""

    highlights: list[HighlightItem] = Field(max_length=4)


class SiteResponse(BaseModel):
    tagline: str | None
    hero_text: str | None
    primary_color: str | None
    secondary_color: str | None
    accent_color: str | None
    has_logo: bool
    has_icon: bool
    # The current version of each policy uploaded so far.
    documents: list[SiteDocumentResponse]
    faqs: list[FaqItem]
    highlights: list[HighlightItem]


class FaqsRequest(BaseModel):
    """The whole list, in order (at most 20: ck_tenant_faqs_limit)."""

    faqs: list[FaqItem] = Field(max_length=20)


class StartSiteUploadRequest(BaseModel):
    kind: SiteFileKind
    # The type the browser says the file is; checked again once stored.
    content_type: Literal["image/png", "image/jpeg", "image/webp", "application/pdf"]


class SiteUploadResponse(BaseModel):
    # Send this back to confirm the upload once the file is stored.
    key: str
    url: str
    fields: dict[str, str]


class ConfirmSiteUploadRequest(BaseModel):
    kind: SiteFileKind
    key: str = Field(min_length=1, max_length=300)


class PublicFaqResponse(BaseModel):
    question: str
    answer: str


class PublicBusinessResponse(BaseModel):
    """The business's landing page: what anyone may see."""

    name: str
    tagline: str | None
    hero_text: str | None
    about: str | None
    email: str | None
    phone: str | None
    primary_color: str | None
    secondary_color: str | None
    accent_color: str | None
    has_logo: bool
    has_privacy: bool
    has_terms: bool
    faqs: list[PublicFaqResponse]
    highlights: list[HighlightItem]
