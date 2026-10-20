import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.child_documents import ChildDocumentNotFoundError
from app.public.repositories.child_document import ChildDocumentRepository
from app.public.schemas.child_documents import ChildDocumentResponse
from app.public.schemas.enums import ChildDocumentUploadStatus


logger = logging.getLogger("app.documents")


class UpdateChildDocumentService:
    """
    A family removing a document. It disappears from view but the record
    and file are kept for the retention period
    (docs/child-document-retention-policy.md). Removing it sends the child
    back to medical review (trg_child_documents_medical_review), and only
    the family may do it (trg_child_documents_rules).
    """

    def __init__(
        self,
        *,
        db: Session,
        document_repository: ChildDocumentRepository,
    ):
        self.db = db
        self.document_repository = document_repository

    @transactional
    def remove(
        self,
        *,
        id: UUID,
    ) -> ChildDocumentResponse:
        # RLS hides other families' documents, so they read as not found.
        document = self.document_repository.get_by_id(id=id)

        if (
            not document
            or not document.is_active
            or document.upload_status != ChildDocumentUploadStatus.UPLOADED
        ):
            raise ChildDocumentNotFoundError()

        self.document_repository.deactivate(document=document)

        logger.info(
            "Document removed",
            extra={
                "event": "child_document_removed",
                "result": "success",
                "reason": f"document_id={id}; child_id={document.child_id}",
            },
        )

        return ChildDocumentResponse.model_validate(document, from_attributes=True)
