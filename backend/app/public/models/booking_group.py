import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class BookingGroup(Base):
    __tablename__ = "booking_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    idempotency_key = Column(String(128), nullable=False)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    source = Column(String(32), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_booking_group_user_idempotency",
        ),
        {"schema": "public"},
    )
