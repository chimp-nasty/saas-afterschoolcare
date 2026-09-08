import uuid

from sqlalchemy import Enum, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

from app.public.models.enums import enum_values, ChildDocumentType, ChildDocumentUploadStatus


class ChildDocument(Base):
    __tablename__ = "child_documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.child_profile.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    uploaded_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "auth.users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    document_type = Column(
        Enum(
            ChildDocumentType,
            name="child_document_type_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )

    filename = Column(
        String(255),
        nullable=False,
    )

    storage_bucket = Column(
        String(255),
        nullable=False,
    )

    storage_object_key = Column(
        Text,
        nullable=False,
    )

    content_type = Column(
        String(100),
        nullable=True,
    )

    size_bytes = Column(
        Integer,
        nullable=True,
    )

    upload_status = Column(
        Enum(
            ChildDocumentUploadStatus,
            name="child_document_upload_status_enum",
            schema="public",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default="pending",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        {"schema": "public"},
    )