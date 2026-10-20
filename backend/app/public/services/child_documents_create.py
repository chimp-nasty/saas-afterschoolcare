import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.db.transaction import transactional
from app.errors.child_documents import (
    ChildDocumentInvalidFileError,
    ChildDocumentNotFoundError,
    ChildDocumentNotReceivedError,
    ChildDocumentTooLargeError,
    ChildDocumentUploadFailedError,
)
from app.errors.children import ChildProfileNotFoundError
from app.errors.storage import StorageProviderError
from app.integrations.storage.client import StorageClient
from app.integrations.storage.file_types import SIGNATURE_LENGTH, detect_content_type
from app.public.repositories.child_document import ChildDocumentRepository
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.child_documents import (
    ChildDocumentResponse,
    ChildDocumentUploadResponse,
    CreateChildDocumentRequest,
    SignedUploadResponse,
)
from app.public.schemas.enums import ChildDocumentUploadStatus
from app.public.services.child_document_storage import (
    MAX_DOCUMENT_SIZE_BYTES,
    UPLOAD_EXPIRES_IN,
    document_key,
    object_metadata,
    pending_key,
)
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.documents")


@dataclass
class _Upload:
    document_id: UUID
    tenant_id: UUID
    location_id: UUID
    child_id: UUID
    storage_provider: str
    bucket: str
    key: str
    content_type: str | None
    upload_status: str


class CreateChildDocumentService:
    """
    A family uploading a document for their child, in three steps:

    1. start: record a pending document and hand the browser a signed
       upload to pending/ in the bucket
    2. the browser uploads the file straight to storage
    3. complete: check the stored file really is what was declared (size,
       type, first bytes), move it to documents/ and accept it

    Accepting it sends the child back to medical review (schema/0004,
    trg_child_documents_medical_review). Who may upload, and for which
    child, is decided by RLS and trg_child_documents_rules.

    No database transaction stays open during storage calls; each step that
    writes afterwards sets the RLS context again.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        document_repository: ChildDocumentRepository,
        child_repository: ChildProfileRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.document_repository = document_repository
        self.child_repository = child_repository
        self.location_repository = location_repository
        self.storage = StorageClient()

    def start(
        self,
        *,
        body: CreateChildDocumentRequest,
        user_id: UUID,
    ) -> ChildDocumentUploadResponse:
        document, upload = self._open(body=body, user_id=user_id)

        expires_at = datetime.now(timezone.utc) + UPLOAD_EXPIRES_IN

        signed = self.storage.create_upload(
            key=upload.key,
            content_type=body.content_type,
            max_size_bytes=MAX_DOCUMENT_SIZE_BYTES,
            metadata=object_metadata(
                tenant_id=upload.tenant_id,
                location_id=upload.location_id,
                child_id=upload.child_id,
                document_id=upload.document_id,
            ),
            expires_in=UPLOAD_EXPIRES_IN,
        )

        return ChildDocumentUploadResponse(
            document=document,
            upload=SignedUploadResponse(
                url=signed.url,
                fields=signed.fields,
                expires_at=expires_at,
            ),
        )

    def complete(
        self,
        *,
        id: UUID,
        user_id: UUID,
        location_id: UUID,
    ) -> ChildDocumentResponse:
        upload = self._get_upload(id=id)

        # Already accepted (e.g. a retry after a lost response).
        if upload.upload_status == ChildDocumentUploadStatus.UPLOADED:
            return self._response(id=id, user_id=user_id, location_id=location_id)

        if upload.upload_status == ChildDocumentUploadStatus.FAILED:
            raise ChildDocumentUploadFailedError()

        if upload.storage_provider != self.storage.provider:
            raise StorageProviderError(
                log_reason=f"document {id} is stored with {upload.storage_provider}, not {self.storage.provider}",
            )

        stored = self.storage.get_object(bucket=upload.bucket, key=upload.key)

        # Left pending: the family can still upload and complete again.
        if stored is None:
            raise ChildDocumentNotReceivedError()

        problem = self._check_file(upload=upload, size_bytes=stored.size_bytes)

        if problem is not None:
            self.storage.delete(bucket=upload.bucket, key=upload.key)
            self._record_failure(id=id, user_id=user_id, location_id=location_id, reason=problem.log_reason)
            raise problem

        final_key = document_key(
            tenant_id=upload.tenant_id,
            location_id=upload.location_id,
            child_id=upload.child_id,
            document_id=upload.document_id,
        )

        self.storage.copy(bucket=upload.bucket, source_key=upload.key, target_key=final_key)

        response = self._record_upload(
            id=id,
            user_id=user_id,
            location_id=location_id,
            key=final_key,
            content_type=upload.content_type,
            size_bytes=stored.size_bytes,
        )

        # The bucket's lifecycle rule clears pending/ anyway, so a failure
        # here only leaves a copy behind for a day.
        try:
            self.storage.delete(bucket=upload.bucket, key=upload.key)
        except StorageProviderError as exc:
            logger.warning(
                "Pending upload not deleted",
                extra={
                    "event": "child_document_pending_not_deleted",
                    "result": "failed",
                    "reason": f"document_id={id}; {exc.log_reason}",
                },
            )

        return response

    @transactional
    def _open(
        self,
        *,
        body: CreateChildDocumentRequest,
        user_id: UUID,
    ) -> tuple[ChildDocumentResponse, _Upload]:
        # RLS: a family sees only their own children.
        child = self.child_repository.get_by_id(id=body.child_id)

        if not child:
            raise ChildProfileNotFoundError()

        tenant_id = self.location_repository.get_by_id(id=child.location_id).tenant_id
        document_id = uuid.uuid4()
        key = pending_key(tenant_id=tenant_id, document_id=document_id)

        # The type and size limits, the child being current and the family
        # owning them are checked here, by the database.
        document = self.document_repository.create(
            id=document_id,
            child_id=child.id,
            uploaded_by_user_id=user_id,
            document_type=body.document_type,
            filename=body.filename,
            storage_provider=self.storage.provider,
            storage_bucket=self.storage.bucket,
            storage_object_key=key,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
        )

        logger.info(
            "Document upload started",
            extra={
                "event": "child_document_upload_started",
                "result": "pending",
                "reason": f"document_id={document_id}; child_id={child.id}; type={body.document_type}",
            },
        )

        return (
            ChildDocumentResponse.model_validate(document, from_attributes=True),
            _Upload(
                document_id=document_id,
                tenant_id=tenant_id,
                location_id=child.location_id,
                child_id=child.id,
                storage_provider=self.storage.provider,
                bucket=self.storage.bucket,
                key=key,
                content_type=body.content_type,
                upload_status=ChildDocumentUploadStatus.PENDING,
            ),
        )

    @transactional
    def _get_upload(
        self,
        *,
        id: UUID,
    ) -> _Upload:
        row = self.document_repository.get_with_owner_by_id(id=id)

        if not row or not row.ChildDocument.is_active:
            raise ChildDocumentNotFoundError()

        document = row.ChildDocument

        return _Upload(
            document_id=document.id,
            tenant_id=row.tenant_id,
            location_id=row.location_id,
            child_id=document.child_id,
            storage_provider=document.storage_provider,
            bucket=document.storage_bucket,
            key=document.storage_object_key,
            content_type=document.content_type,
            upload_status=document.upload_status,
        )

    def _check_file(
        self,
        *,
        upload: _Upload,
        size_bytes: int,
    ) -> ChildDocumentTooLargeError | ChildDocumentInvalidFileError | None:
        """
        The stored file, not what the browser said about it. The upload
        policy already limits size and type; this is the second check, and
        the only one that looks inside the file.
        """
        if size_bytes > MAX_DOCUMENT_SIZE_BYTES:
            return ChildDocumentTooLargeError(log_reason=f"size_bytes={size_bytes}")

        head = self.storage.read_start(bucket=upload.bucket, key=upload.key, length=SIGNATURE_LENGTH)
        detected = detect_content_type(head)

        if detected != upload.content_type:
            return ChildDocumentInvalidFileError(
                log_reason=f"declared={upload.content_type}; detected={detected}",
            )

        return None

    @transactional
    def _record_upload(
        self,
        *,
        id: UUID,
        user_id: UUID,
        location_id: UUID,
        key: str,
        content_type: str,
        size_bytes: int,
    ) -> ChildDocumentResponse:
        self._restore_rls(user_id=user_id, location_id=location_id)

        document = self.document_repository.get_by_id(id=id)

        self.document_repository.mark_uploaded(
            document=document,
            storage_object_key=key,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        logger.info(
            "Document uploaded",
            extra={
                "event": "child_document_uploaded",
                "result": "success",
                "reason": f"document_id={id}; child_id={document.child_id}; size_bytes={size_bytes}",
            },
        )

        return ChildDocumentResponse.model_validate(document, from_attributes=True)

    @transactional
    def _record_failure(
        self,
        *,
        id: UUID,
        user_id: UUID,
        location_id: UUID,
        reason: str | None,
    ) -> None:
        self._restore_rls(user_id=user_id, location_id=location_id)

        document = self.document_repository.get_by_id(id=id)

        self.document_repository.mark_failed(document=document)

        logger.warning(
            "Document upload rejected",
            extra={
                "event": "child_document_upload_rejected",
                "result": "failed",
                "reason": f"document_id={id}; {reason}",
            },
        )

    @transactional
    def _response(
        self,
        *,
        id: UUID,
        user_id: UUID,
        location_id: UUID,
    ) -> ChildDocumentResponse:
        self._restore_rls(user_id=user_id, location_id=location_id)

        return ChildDocumentResponse.model_validate(
            self.document_repository.get_by_id(id=id),
            from_attributes=True,
        )

    def _restore_rls(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        # The RLS settings last one transaction; each later step sets them
        # again for the same user and location.
        self.rls_context.set_user_id(user_id=user_id)
        self.rls_context.set_location_id(location_id=location_id)
