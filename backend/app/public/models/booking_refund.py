import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


class BookingRefund(Base):
    __tablename__ = "booking_refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(UUID(as_uuid=True), ForeignKey("public.bookings.id"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("public.invoices.id"), nullable=False)

    invoice_booking_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.invoice_booking_items.id"),
        nullable=False,
    )

    parent_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    requested_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    amount_cents = Column(Integer, nullable=False)

    currency = Column(
        ENUM("AUD", "NZD", "USD", name="currency_code_enum", create_type=False),
        nullable=False,
    )

    status = Column(String(32), nullable=False, server_default="PENDING")
    reason = Column(Text, nullable=True)

    stripe_payment_intent_id = Column(String(255), nullable=False)
    stripe_refund_id = Column(String(255), nullable=True)

    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_booking_refund_booking"),
        {"schema": "public"},
    )
