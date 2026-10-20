from uuid import UUID
from datetime import date, datetime, time

from pydantic import BaseModel

from app.db.repository import Pagination
from app.public.schemas.enums import (
    BookingGroupScope,
    BookingStatus,
    CurrencyCode,
    PaymentStatus,
    RefundStatus,
    StripeStatus,
)


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

    # The session's times, in the location's timezone.
    start_time: time
    end_time: time

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


class BookingGroupLineResponse(BookingTableResponse):
    """One child on one day in the review screen, with its refund window."""

    # The last day (location time) the family can refund it, inclusive.
    refundable_until: date
    is_refundable: bool

    # Its latest refund, if any: PENDING while Stripe processes it.
    refund_status: RefundStatus | None


class BookingGroupResponse(BaseModel):
    """A booking group for the review screen (pay or cancel a pending one)."""

    booking_group_id: UUID

    # PENDING while it can still be paid or cancelled; a lapsed hold reads
    # as EXPIRED.
    status: BookingStatus

    # When its payment succeeded; None until then (and for payments made
    # before paid_at was recorded).
    paid_at: datetime | None

    # Stripe's receipt for the payment; None until paid, or if Stripe
    # couldn't give it when the payment settled.
    receipt_url: str | None

    total_cents: int
    currency: CurrencyCode

    bookings: list[BookingGroupLineResponse]


class CheckoutUrlResponse(BaseModel):
    checkout_url: str


# Inherits page/limit (see ListBookingsFilterRequest).
class ListBookingGroupsFilterRequest(Pagination):
    # UPCOMING: still to come (last day today or later) and pending or
    # confirmed. HISTORY: everything else. None lists both.
    scope: BookingGroupScope | None = None


class BookingGroupSummaryResponse(BaseModel):
    """One card in "My bookings": a checkout and what it covers."""

    booking_group_id: UUID
    created_at: datetime

    status: BookingStatus
    paid_at: datetime | None

    service_name: str
    child_names: list[str]

    first_date: date
    last_date: date
    booking_count: int

    total_cents: int
    currency: CurrencyCode
