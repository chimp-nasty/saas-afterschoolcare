import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


payment_status_enum = ENUM(
    "PENDING",
    "PAID",
    "REFUNDED",
    "FAILED",
    name="payment_status_enum",
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


class Booking(Base):
    __tablename__ = "bookings"

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

    booking_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.booking_groups.id"),
        nullable=False,
    )

    location_service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.location_service_days.id"),
        nullable=False,
    )

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id"),
        nullable=False,
    )

    payment_status = Column(
        payment_status_enum,
        nullable=False,
        server_default="PENDING",
    )

    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    price_snapshot_cents = Column(Integer, nullable=False)

    currency = Column(currency_code_enum, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "child_id",
            "location_service_id",
            name="uq_booking_child_location_service",
        ),
        {"schema": "public"},
    )
