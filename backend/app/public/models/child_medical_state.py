from sqlalchemy import Enum, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

from app.public.models.enums import enum_values, MedicalReviewStatus


class ChildMedicalState(Base):
    __tablename__ = "child_medical_state"

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.child_profile.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    review_status = Column(
        Enum(
            MedicalReviewStatus,
            name="medical_review_status_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default="not_required",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )

    __table_args__ = (
        {"schema": "public"},
    )