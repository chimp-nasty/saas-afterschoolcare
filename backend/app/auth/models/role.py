import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    code = Column(String(100), nullable=False, unique=True)
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z][a-z0-9_]*$'",
            name="roles_code_format_check",
        ),
        {"schema": "auth"},
    )
