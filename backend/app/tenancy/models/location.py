import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenancy.tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name = Column(
        String(200),
    )

    code = Column(
        String(50),
        nullable=False,
    )

    address = Column(
        Text,
        nullable=True,
    )

    phone = Column(
        String(50),
        nullable=True,
    )

    email = Column(
        String(255),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_location_tenant_code",
        ),
        CheckConstraint(
            "code ~ '^[a-z][a-z0-9-]*$'",
            name="locations_code_format_check",
        ),
        {"schema": "tenancy"},
    )
