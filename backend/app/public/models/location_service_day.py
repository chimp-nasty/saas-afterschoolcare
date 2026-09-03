import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class LocationServiceDay(Base):
    __tablename__ = "location_service_days"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    location_service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.location_services.id"),
        nullable=False,
    )

    service_date = Column(Date, nullable=False)

    is_open = Column(Boolean, nullable=False, server_default="true")
    capacity = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "location_service_id",
            "service_date",
            name="uq_location_service_day",
        ),
        {"schema": "public"},
    )
