import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class InvoiceBookingItem(Base):
    __tablename__ = "invoice_booking_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.invoices.id", ondelete="CASCADE"),
        nullable=False,
    )

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.bookings.id"),
        nullable=False,
    )

    line_description = Column(String(255), nullable=False)
    amount_cents = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_invoice_booking_item_booking"),
        {"schema": "public"},
    )
