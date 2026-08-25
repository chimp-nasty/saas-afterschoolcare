import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    parent_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)

    status_id = Column(
        SmallInteger,
        ForeignKey("public.invoice_statuses.id"),
        nullable=False,
    )

    subtotal_cents = Column(Integer, nullable=False)
    discount_cents = Column(Integer, nullable=False, server_default="0")
    total_cents = Column(Integer, nullable=False)

    currency = Column(
        ENUM("AUD", "NZD", "USD", name="currency_code_enum", create_type=False),
        nullable=False,
    )

    issued_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    stripe_customer_id = Column(String(255), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    stripe_receipt_url = Column(Text, nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_checkout_session_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
