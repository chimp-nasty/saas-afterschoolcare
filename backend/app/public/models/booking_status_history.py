import uuid

from sqlalchemy import Column, DateTime, ForeignKey, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    old_status_id = Column(
        SmallInteger,
        ForeignKey("public.booking_statuses.id"),
        nullable=True,
    )

    new_status_id = Column(
        SmallInteger,
        ForeignKey("public.booking_statuses.id"),
        nullable=False,
    )

    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    changed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )

    note = Column(Text, nullable=True)
