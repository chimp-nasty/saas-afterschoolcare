from uuid import UUID

from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import ChildDocument, ChildProfile, Location
from app.public.schemas.enums import ChildDocumentUploadStatus


class ChildDocumentRepository(Repository):
    def create(
        self,
        *,
        id: UUID,
        child_id: UUID,
        uploaded_by_user_id: UUID,
        document_type: str,
        filename: str,
        storage_provider: str,
        storage_bucket: str,
        storage_object_key: str,
        content_type: str | None = None,
        size_bytes: int | None = None,
    ) -> ChildDocument:
        record = ChildDocument(
            id=id,
            child_id=child_id,
            uploaded_by_user_id=uploaded_by_user_id,
            document_type=document_type,
            filename=filename,
            storage_provider=storage_provider,
            storage_bucket=storage_bucket,
            storage_object_key=storage_object_key,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildDocument | None:
        return (
            self.db.query(ChildDocument)
            .filter(ChildDocument.id == id)
            .first()
        )

    def get_with_owner_by_id(
        self,
        *,
        id: UUID,
    ) -> Row | None:
        """
        The document with the tenant and location of its child, which its
        object key must start with.
        """
        return (
            self.db.query(
                ChildDocument,
                ChildProfile.location_id,
                Location.tenant_id,
            )
            .join(
                ChildProfile,
                ChildProfile.id == ChildDocument.child_id,
            )
            .join(
                Location,
                Location.id == ChildProfile.location_id,
            )
            .filter(ChildDocument.id == id)
            .first()
        )

    def list_current_for_child(
        self,
        *,
        child_id: UUID,
    ) -> list[ChildDocument]:
        """Uploaded documents the family hasn't removed, newest first."""
        return (
            self.db.query(ChildDocument)
            .filter(
                ChildDocument.child_id == child_id,
                ChildDocument.is_active.is_(True),
                ChildDocument.upload_status == ChildDocumentUploadStatus.UPLOADED,
            )
            .order_by(
                ChildDocument.created_at.desc(),
                ChildDocument.id.desc(),
            )
            .all()
        )

    def mark_uploaded(
        self,
        *,
        document: ChildDocument,
        storage_object_key: str,
        content_type: str,
        size_bytes: int,
    ) -> ChildDocument:
        document.storage_object_key = storage_object_key
        document.content_type = content_type
        document.size_bytes = size_bytes
        document.upload_status = ChildDocumentUploadStatus.UPLOADED

        self.db.flush()

        return document

    def mark_failed(
        self,
        *,
        document: ChildDocument,
    ) -> ChildDocument:
        document.upload_status = ChildDocumentUploadStatus.FAILED

        self.db.flush()

        return document

    def deactivate(
        self,
        *,
        document: ChildDocument,
    ) -> ChildDocument:
        document.is_active = False

        self.db.flush()

        return document
