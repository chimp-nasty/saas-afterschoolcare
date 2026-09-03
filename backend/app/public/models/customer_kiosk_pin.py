import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CustomerKioskPin(Base):
    __tablename__ = "customer_kiosk_pins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    pin_hash = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_user_kiosk_pin",
        ),
        {"schema": "public"},
    )
