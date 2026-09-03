import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    signed_in_at = Column(DateTime(timezone=True), nullable=True)
    signed_out_at = Column(DateTime(timezone=True), nullable=True)

    signed_in_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )

    signed_out_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "booking_id",
            name="uq_attendance_record_booking",
        ),
        CheckConstraint(
            "signed_out_at IS NULL OR signed_in_at IS NOT NULL",
            name="attendance_signout_requires_signin",
        ),
        CheckConstraint(
            "signed_out_at IS NULL OR signed_out_at >= signed_in_at",
            name="attendance_signout_after_signin",
        ),
        {"schema": "public"},
    )
