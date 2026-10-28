from datetime import date, datetime

from pydantic import BaseModel


class DashboardNumbersResponse(BaseModel):
    """
    One period's numbers (docs/owner-dashboard.md). Sessions count by when
    they take place; sign-ups, refunds and cancellations by when they
    happened, so those are None for a week still to come.
    """

    revenue_cents: int
    currency: str | None
    bookings: int
    active_families: int
    returning_families: int
    # Bookings per active family (None with no active families).
    average_sessions: float | None
    registrations: int | None
    refunds: int | None
    refunded_cents: int | None
    # Paid sessions cancelled without a refund in the period.
    cancelled_unrefunded: int | None


class UnrefundedPaymentResponse(BaseModel):
    """A payment taken after its places were released: refund it in Stripe, found by its reference."""

    reference: str
    location_name: str
    total_cents: int
    currency: str
    paid_at: datetime | None


class DashboardAttentionResponse(BaseModel):
    """What needs the owner's attention now, whatever the period."""

    reviews_pending: int
    documents_requested: int
    enquiries_new: int
    reactivation_requests: int
    inactive_families: int
    unrefunded_payments: list[UnrefundedPaymentResponse]


class OwnerDashboardResponse(BaseModel):
    # The Monday-to-Sunday week shown, in weeks from this one (-1 last
    # week, 1 next week, each centre's own timezone); None for all time.
    week: int | None
    # Its dates (the first centre's; None for all time).
    from_date: date | None
    to_date: date | None
    current: DashboardNumbersResponse
    # The week before, to compare with (None for all time).
    previous: DashboardNumbersResponse | None
    attention: DashboardAttentionResponse
