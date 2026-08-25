import uuid

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.permissions.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permission",
        ),
        {"schema": "auth"},
    )
