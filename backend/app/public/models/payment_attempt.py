import uuid

from sqlalchemy import Enum, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


from app.public.models.enums import enum_values, StripeStatus, CurrencyCode


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

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
        Enum(
            StripeStatus,
            name="stripe_status_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default="PENDING",
    )

    stripe_payment_intent_id = Column(
        String(255),
        nullable=True,
        unique=True,
    )

    stripe_checkout_session_id = Column(
        String(255),
        nullable=True,
        unique=True,
    )

    stripe_receipt_url = Column(
        Text,
        nullable=True,
    )

    booking_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.booking_groups.id"),
        nullable=False,
    )

    total_cents = Column(
        Integer,
        nullable=False,
    )

    currency = Column(
        Enum(
            CurrencyCode,
            name="currency_code_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        {"schema": "public"},
    )