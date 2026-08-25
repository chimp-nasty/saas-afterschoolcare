import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class LocationBranding(Base):
    __tablename__ = "location_branding"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenancy.locations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    display_name = Column(
        String(200),
        nullable=True,
    )

    logo_key = Column(
        Text,
        nullable=True,
    )

    primary_color = Column(
        String(50),
        nullable=True,
    )

    secondary_color = Column(
        String(50),
        nullable=True,
    )

    font_family = Column(
        String(100),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            name="uq_location_branding_location",
        ),
        {"schema": "tenancy"},
    )
