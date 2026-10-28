from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.tenancy.schemas.site import Colour, PhotoAlt, PhotoResponse


# The platform's landing page (docs/platform-site.md): its words, branding,
# photos and feature cards, like a business's site (app/tenancy/schemas/site.py).

# What can be uploaded: the two images and the two photos.
PlatformFileKind = Literal["logo", "icon", "hero_photo", "about_photo"]

# The icons a feature card can have (ck_platform_features_icon).
PlatformFeatureIcon = Literal[
    "location", "privacy", "lock", "staff", "family", "medical",
    "booking", "payment", "kiosk", "email", "dashboard", "document",
]


class PlatformSiteRequest(BaseModel):
    """
    The page's words and colours. Only the fields sent are changed, so each
    editor on the page sends its own. A field sent empty is cleared
    (colours: back to the app's defaults).
    """

    headline: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    hero_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    about_title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    about: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None
    primary_color: Colour | None = None
    secondary_color: Colour | None = None
    accent_color: Colour | None = None
    hero_photo_alt: PhotoAlt | None = None
    about_photo_alt: PhotoAlt | None = None

    @field_validator(
        "headline",
        "hero_text",
        "about_title",
        "about",
        "primary_color",
        "secondary_color",
        "accent_color",
        "hero_photo_alt",
        "about_photo_alt",
        mode="before",
    )
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value or None


class PlatformFeatureItem(BaseModel):
    icon: PlatformFeatureIcon
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class PlatformFeaturesRequest(BaseModel):
    """The whole list, in order (at most 9: ck_platform_features_limit)."""

    features: list[PlatformFeatureItem] = Field(max_length=9)


class StartPlatformUploadRequest(BaseModel):
    kind: PlatformFileKind
    # The type the browser says the file is; checked again once stored.
    content_type: Literal["image/png", "image/jpeg", "image/webp"]


class ConfirmPlatformUploadRequest(BaseModel):
    kind: PlatformFileKind
    # The upload's key, from its start.
    key: str = Field(min_length=1, max_length=300)


class PlatformSiteResponse(BaseModel):
    """The landing page and the platform's branding: what anyone may see."""

    headline: str | None
    hero_text: str | None
    about_title: str | None
    about: str | None
    hero_photo: PhotoResponse | None
    about_photo: PhotoResponse | None
    primary_color: str | None
    secondary_color: str | None
    accent_color: str | None
    has_logo: bool
    has_icon: bool
    features: list[PlatformFeatureItem]
