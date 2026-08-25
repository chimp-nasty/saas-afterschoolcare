import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ChildDocument(Base):
    __tablename__ = "child_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id", ondelete="CASCADE"),
        nullable=False,
    )

    uploaded_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_type = Column(String(64), nullable=False)
    original_filename = Column(String(255), nullable=False)

    storage_bucket = Column(String(255), nullable=False)
    storage_object_key = Column(Text, nullable=False)

    content_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)

    upload_status = Column(String(32), nullable=False, server_default="pending")
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('medical_action_plan', 'asthma_action_plan', "
            "'allergy_anaphylaxis_plan', 'medication_authorisation', "
            "'other_supporting_document')",
            name="child_document_type_check",
        ),
        CheckConstraint(
            "upload_status IN ('pending', 'uploaded', 'failed', 'deleted')",
            name="child_document_upload_status_check",
        ),
        {"schema": "public"},
    )
