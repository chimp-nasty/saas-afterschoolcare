import uuid

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class LocationUserRole(Base):
    __tablename__ = "location_user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenancy.locations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "location_id",
            "role_id",
            name="uq_location_user_role",
        ),
        {"schema": "auth"},
    )
