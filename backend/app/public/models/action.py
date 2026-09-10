import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id", ondelete="CASCADE"),
        nullable=True,
    )

    target = Column(
        Text,
        nullable=False,
    )

    title = Column(
        Text,
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    cited_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        {"schema": "public"},
    )