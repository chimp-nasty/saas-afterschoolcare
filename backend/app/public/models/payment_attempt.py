import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


stripe_status_enum = ENUM(
    "PENDING",
    "SUCCEEDED",
    "FAILED",
    name="stripe_status_enum",
    schema="public",
    create_type=False,
)

currency_code_enum = ENUM(
    "AUD",
    "NZD",
    "USD",
    name="currency_code_enum",
    schema="public",
    create_type=False,
)


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenancy.locations.id"),
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    stripe_status = Column(
        stripe_status_enum,
        nullable=False,
        server_default="PENDING",
    )

    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True)
    stripe_checkout_session_id = Column(String(255), nullable=True, unique=True)

    stripe_receipt_url = Column(Text, nullable=True)

    booking_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.booking_groups.id"),
        nullable=False,
    )

    total_cents = Column(Integer, nullable=False)

    currency = Column(currency_code_enum, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        {"schema": "public"},
    )
