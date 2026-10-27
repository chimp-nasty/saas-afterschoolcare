from uuid import UUID

from pydantic import BaseModel

from app.tenancy.schemas.site import PhotoResponse


class PublicLocationResponse(BaseModel):
    tenant_name: str
    tenant_code: str

    location_id: UUID
    location_code: str
    location_name: str

    # Where its services run, and how to reach it.
    address_line_1: str
    address_line_2: str | None
    suburb: str
    state: str
    postcode: str

    # For maps; None until the address has been geocoded.
    latitude: float | None
    longitude: float | None
    google_place_id: str | None

    phone: str | None
    email: str | None

    # Its own photo (stage 9b), else none: pages then use the business's.
    photo: PhotoResponse | None

    # The business's branding (one brand per business: tenant_branding).
    has_logo: bool
    primary_color: str | None
    secondary_color: str | None
    accent_color: str | None