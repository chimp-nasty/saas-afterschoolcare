from uuid import UUID
from datetime import date, datetime

from pydantic import BaseModel

from app.db.repository import Pagination
from app.public.schemas.enums import BookingStatus, CurrencyCode, PaymentStatus, StripeStatus


class BookingSelection(BaseModel):
    child_id: UUID
    location_service_days: list[UUID]


class CreateBookingRequest(BaseModel):
    idempotency_key: str
    bookings: list[BookingSelection]


class CreateBookingResponse(BaseModel):
    idempotency_key: str
    amount: int
    booking_group_id: UUID

    # Stripe's hosted payment page; the frontend redirects here.
    checkout_url: str | None


class BookingConflictRow(BaseModel):
    child_id: UUID
    child_name: str

    location_service_day_id: UUID
    location_service_date: date


# Inherits page/limit: FastAPI only expands a query model when it's the
# route's only query parameter.
class ListBookingsFilterRequest(Pagination):
    booking_status: list[BookingStatus] | None = None
    payment_status: list[PaymentStatus] | None = None
    date_from: date | None = None
    date_to: date | None = None


class BookingResponse(BaseModel):
    id: UUID
    location_id: UUID
    user_id: UUID
    booking_group_id: UUID
    location_service_day_id: UUID
    child_id: UUID

    child_name: str
    service_date: date
    service_name: str

    booking_status: BookingStatus
    payment_status: PaymentStatus
    cancelled_at: datetime | None

    price_snapshot_cents: int
    currency: CurrencyCode

    created_at: datetime
    updated_at: datetime


class BookingTableResponse(BaseModel):
    id: UUID
    location_id: UUID
    user_id: UUID
    booking_group_id: UUID
    location_service_day_id: UUID
    child_id: UUID

    child_name: str
    service_date: date
    service_name: str

    booking_status: BookingStatus
    payment_status: PaymentStatus

    price_snapshot_cents: int
    currency: CurrencyCode


class CheckoutStatusResponse(BaseModel):
    booking_group_id: UUID

    # PENDING until the Stripe webhook lands, then SUCCEEDED or FAILED.
    payment_status: StripeStatus

    total_cents: int
    currency: CurrencyCode

    bookings: list[BookingTableResponse]


class BookingGroupResponse(BaseModel):
    """A booking group for the review screen (pay or cancel a pending one)."""

    booking_group_id: UUID

    # PENDING while it can still be paid or cancelled; a lapsed hold reads
    # as EXPIRED.
    status: BookingStatus

    total_cents: int
    currency: CurrencyCode

    bookings: list[BookingTableResponse]


class CheckoutUrlResponse(BaseModel):
    checkout_url: str


# Inherits page/limit (see ListBookingsFilterRequest).
class ListBookingGroupsFilterRequest(Pagination):
    pass


class BookingGroupSummaryResponse(BaseModel):
    """One card in "My bookings": a checkout and what it covers."""

    booking_group_id: UUID
    created_at: datetime

    status: BookingStatus

    service_name: str
    child_names: list[str]

    first_date: date
    last_date: date
    booking_count: int

    total_cents: int
    currency: CurrencyCode
