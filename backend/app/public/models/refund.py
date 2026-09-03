import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.bookings.id"),
        nullable=False,
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

    requested_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    reason = Column(Text, nullable=True)

    stripe_refund_id = Column(String(255), nullable=True, unique=True)

    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        {"schema": "public"},
    )
