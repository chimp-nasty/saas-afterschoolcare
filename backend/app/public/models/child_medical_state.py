from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


medical_review_status_enum = ENUM(
    "not_required",
    "pending",
    "documentation_requested",
    "approved",
    name="medical_review_status_enum",
    schema="public",
    create_type=False,
)


class ChildMedicalState(Base):
    __tablename__ = "child_medical_state"

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id", ondelete="CASCADE"),
        primary_key=True,
    )

    review_status = Column(
        medical_review_status_enum,
        nullable=False,
        server_default="not_required",
    )

    updated_at = Column(DateTime(timezone=True), nullable=True)

    updated_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )

    __table_args__ = (
        {"schema": "public"},
    )
