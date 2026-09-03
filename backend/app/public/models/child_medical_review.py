import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ChildMedicalReview(Base):
    __tablename__ = "child_medical_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id", ondelete="CASCADE"),
        nullable=False,
    )

    reviewed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        {"schema": "public"},
    )
