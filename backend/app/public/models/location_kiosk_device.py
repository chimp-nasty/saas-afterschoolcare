import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class LocationKioskDevice(Base):
    __tablename__ = "location_kiosk_devices"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenancy.locations.id"),
        nullable=False,
    )

    name = Column(Text, nullable=False)
    setup_secret_hash = Column(Text, nullable=True)
    token_version = Column(Integer, nullable=False, server_default="1")
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    paired_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
