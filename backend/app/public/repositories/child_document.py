from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.child_document import ChildDocument


class ChildDocumentRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        child_id: UUID,
        uploaded_by_user_id: UUID,
        document_type: str,
        filename: str,
        storage_bucket: str,
        storage_object_key: str,
        content_type: str | None = None,
        size_bytes: int | None = None,
        upload_status: str = "pending",
        is_active: bool = True,
    ) -> ChildDocument:
        record = ChildDocument(
            child_id=child_id,
            uploaded_by_user_id=uploaded_by_user_id,
            document_type=document_type,
            filename=filename,
            storage_bucket=storage_bucket,
            storage_object_key=storage_object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            upload_status=upload_status,
            is_active=is_active,
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
