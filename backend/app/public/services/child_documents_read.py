import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.child_documents import ChildDocumentNotFoundError
from app.errors.children import ChildProfileNotFoundError
from app.errors.storage import StorageProviderError
from app.integrations.storage.client import StorageClient
from app.public.repositories.child_document import ChildDocumentRepository
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.child_documents import (
    ChildDocumentDownloadResponse,
    ChildDocumentResponse,
)
from app.public.schemas.enums import ChildDocumentUploadStatus
from app.public.services.child_document_storage import DOWNLOAD_EXPIRES_IN, document_key


logger = logging.getLogger("app.documents")


class ReadChildDocumentService:
    """
    A child's current documents, and short-lived links to view them. RLS
    decides who sees what: the family their own children's, staff their
    location's. Every link issued is logged (who, which document).
    """

    def __init__(
        self,
        *,
        db: Session,
        document_repository: ChildDocumentRepository,
        child_repository: ChildProfileRepository,
    ):
        self.db = db
        self.document_repository = document_repository
        self.child_repository = child_repository
        self.storage = StorageClient()

    def list_for_child(
        self,
        *,
        child_id: UUID,
    ) -> list[ChildDocumentResponse]:
        if not self.child_repository.get_by_id(id=child_id):
            raise ChildProfileNotFoundError()

        return [
            ChildDocumentResponse.model_validate(document, from_attributes=True)
            for document in self.document_repository.list_current_for_child(child_id=child_id)
        ]

    def create_download(
        self,
        *,
        id: UUID,
    ) -> ChildDocumentDownloadResponse:
        row = self.document_repository.get_with_owner_by_id(id=id)

        if (
            not row
            or not row.ChildDocument.is_active
            or row.ChildDocument.upload_status != ChildDocumentUploadStatus.UPLOADED
        ):
            raise ChildDocumentNotFoundError()

        document = row.ChildDocument

        if document.storage_provider != self.storage.provider:
            raise StorageProviderError(
                log_reason=f"document {id} is stored with {document.storage_provider}, not {self.storage.provider}",
            )

        # The second check before signing: the key must be this document's
        # own, under its child's tenant and location. Anything else means
        # the row is wrong, so nothing is signed.
        expected_key = document_key(
            tenant_id=row.tenant_id,
            location_id=row.location_id,
            child_id=document.child_id,
            document_id=document.id,
        )

        if document.storage_object_key != expected_key:
            logger.error(
                "Document key doesn't match its owner",
                extra={
                    "event": "child_document_key_mismatch",
                    "result": "denied",
                    "reason": f"document_id={id}",
                },
            )
            raise ChildDocumentNotFoundError()

        expires_at = datetime.now(timezone.utc) + DOWNLOAD_EXPIRES_IN

        url = self.storage.create_download_url(
            bucket=document.storage_bucket,
            key=document.storage_object_key,
            content_type=document.content_type,
            filename=document.filename,
            expires_in=DOWNLOAD_EXPIRES_IN,
        )

        logger.info(
            "Document link issued",
            extra={
                "event": "child_document_link_issued",
                "result": "success",
                "reason": f"document_id={id}; child_id={document.child_id}",
            },
        )

        return ChildDocumentDownloadResponse(url=url, expires_at=expires_at)
