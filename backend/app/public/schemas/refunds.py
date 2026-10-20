from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.public.schemas.enums import CurrencyCode, RefundStatus


class CreateRefundRequest(BaseModel):
    booking_id: UUID


class RefundResponse(BaseModel):
    """
    A refund once it's been sent to Stripe. PENDING until the webhook
    confirms it; the booking is cancelled and its place released then.
    """

    id: UUID
    booking_id: UUID

    status: RefundStatus

    amount_cents: int
    currency: CurrencyCode

    created_at: datetime
