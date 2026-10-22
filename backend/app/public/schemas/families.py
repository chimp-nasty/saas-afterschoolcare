from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.public.schemas.attendance import RollPickupPersonResponse
from app.public.schemas.enums import AustralianState, CurrencyCode, EmergencyRelation, MedicalReviewStatus


class FamilySearchFilterRequest(BaseModel):
    # A child's or parent's name, an email or a phone number.
    q: str = Field(min_length=2, max_length=100)


class FamilySearchResultResponse(BaseModel):
    """A family at this centre, as the search lists it."""

    user_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    # Their current children's first names, e.g. "Emma, Noah".
    children: str | None
    # Confirmed bookings from today on.
    upcoming: int
    # Bookings still awaiting payment.
    unpaid: int


class FamilyChildResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    dob: date
    is_active: bool
    review_status: MedicalReviewStatus


class FamilyResponse(BaseModel):
    """A family's page: the parent's details, children and pickup people."""

    user_id: UUID
    first_name: str
    last_name: str
    email: str

    phone: str | None
    address_line_1: str | None
    address_line_2: str | None
    suburb: str | None
    state: AustralianState | None
    postcode: str | None

    # The family's emergency contact (they keep it up to date; read-only here).
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: EmergencyRelation | None
    emergency_contact_relation_other: str | None

    children: list[FamilyChildResponse]
    pickups: list[RollPickupPersonResponse]


class FamilyDateRangeRequest(BaseModel):
    date_from: date | None = None
    date_to: date | None = None


class FamilyAttendanceResponse(BaseModel):
    """One child's session in the attendance history."""

    booking_id: UUID
    service_date: date
    service_name: str
    child_first_name: str
    child_last_name: str

    signed_in_at: datetime | None
    signed_in_by: str | None
    signed_out_at: datetime | None
    signed_out_by: str | None
    collected_by: str | None
    collector_id_sighted: bool | None
    released_to_name: str | None
    release_note: str | None
    sent_to_school: bool
    # Signed out after the session ended (or never signed out).
    left_late: bool


class FamilyPaymentResponse(BaseModel):
    """One payment (a checkout) and what's been refunded from it."""

    id: UUID
    created_at: datetime
    paid_at: datetime | None
    total_cents: int
    currency: CurrencyCode
    stripe_status: str
    receipt_url: str | None
    bookings: int
    refunded_cents: int
