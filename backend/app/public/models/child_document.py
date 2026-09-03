import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID

from app.db.base import Base


child_document_type_enum = ENUM(
    "medical_action_plan",
    "asthma_action_plan",
    "allergy_anaphylaxis_plan",
    "other",
    name="child_document_type_enum",
    schema="public",
    create_type=False,
)

child_document_upload_status_enum = ENUM(
    "pending",
    "uploaded",
    "failed",
    name="child_document_upload_status_enum",
    schema="public",
    create_type=False,
)


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

    document_type = Column(child_document_type_enum, nullable=False)

    filename = Column(String(255), nullable=False)

    storage_bucket = Column(String(255), nullable=False)
    storage_object_key = Column(Text, nullable=False)

    content_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)

    upload_status = Column(
        child_document_upload_status_enum,
        nullable=False,
        server_default="pending",
    )

    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        {"schema": "public"},
    )
