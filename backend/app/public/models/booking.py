import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.booking_groups.id"),
        nullable=True,
    )

    parent_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)
    child_id = Column(UUID(as_uuid=True), ForeignKey("public.child_profile.id"), nullable=False)

    location_service_day_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.location_service_days.id"),
        nullable=False,
    )

    booking_status_id = Column(
        SmallInteger,
        ForeignKey("public.booking_statuses.id"),
        nullable=False,
    )

    payment_status_id = Column(
        SmallInteger,
        ForeignKey("public.payment_statuses.id"),
        nullable=False,
    )

    booked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    price_snapshot_cents = Column(Integer, nullable=False)

    currency = Column(
        ENUM("AUD", "NZD", "USD", name="currency_code_enum", create_type=False),
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
