import uuid

from sqlalchemy import Enum, Column, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

from app.public.models.enums import enum_values, BookingStatus, PaymentStatus, CurrencyCode


class Booking(Base):
    __tablename__ = "bookings"

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

    booking_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.booking_groups.id"),
        nullable=False,
    )

    location_service_day_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.location_service_days.id"),
        nullable=False,
    )

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id"),
        nullable=False,
    )

    booking_status = Column(
        Enum(
            BookingStatus,
            name="booking_status_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default="PENDING",
    )

    payment_status = Column(
        Enum(
            PaymentStatus,
            name="payment_status_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default="PENDING",
    )

    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    price_snapshot_cents = Column(
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

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "uq_active_booking_child_location_service_day",
            "child_id",
            "location_service_day_id",
            unique=True,
            postgresql_where=text(
                "booking_status IN ('PENDING', 'CONFIRMED')"
            ),
        ),
        {"schema": "public"},
    )