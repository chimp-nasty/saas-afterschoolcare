import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class LocationService(Base):
    __tablename__ = "location_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenancy.locations.id"),
        nullable=False,
    )

    service_type_id = Column(
        SmallInteger,
        ForeignKey("public.service_types.id"),
        nullable=False,
    )

    stripe_product_id = Column(String(255), nullable=True, unique=True)
    stripe_price_id = Column(String(255), nullable=True, unique=True)

    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "service_type_id",
            name="uq_location_service_type",
        ),
        {"schema": "public"},
    )
