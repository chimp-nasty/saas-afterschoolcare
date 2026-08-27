import uuid

from sqlalchemy import Boolean, Column, DateTime, String, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "tenancy"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name = Column(
        String(200),
        nullable=False,
    )

    code = Column(
        String(50),
        nullable=False,
        unique=True,
    )

    custom_domain = Column(
        String(255),
        nullable=True,
        unique=True,
    )
    
    email = Column(
        String(255),
        nullable=True,
    )

    terms_accepted_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    terms_version = Column(
        String(50),
        nullable=False,
        server_default="v1",
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
        CheckConstraint(
            "code ~ '^[a-z][a-z0-9-]*$'",
            name="tenants_code_format_check",
        ),
        {"schema": "tenancy"},
    )