import uuid

from sqlalchemy import CheckConstraint, Column, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    resource = Column(String(100), nullable=False)
    action = Column(String(1), nullable=False)
    description = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "resource",
            "action",
            name="uq_permission_resource_action",
        ),
        CheckConstraint(
            "action IN ('c', 'r', 'u', 'd')",
            name="permissions_action_check",
        ),
        CheckConstraint(
            "resource ~ '^[a-z][a-z0-9_]*$'",
            name="permissions_resource_format_check",
        ),
        {"schema": "auth"},
    )
