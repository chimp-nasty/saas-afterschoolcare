from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.public.schemas.enums import ChildDocumentType, ChildDocumentUploadStatus


class ChildDocumentResponse(BaseModel):
    """A document as families and staff see it; where it's stored stays server-side."""

    id: UUID
    child_id: UUID

    document_type: ChildDocumentType
    filename: str
    content_type: str | None
    size_bytes: int | None

    upload_status: ChildDocumentUploadStatus
    is_active: bool

    created_at: datetime


class ListChildDocumentsFilterRequest(BaseModel):
    child_id: UUID


class CreateChildDocumentRequest(BaseModel):
    """
    Start uploading one file. The type and size are what the browser
    reports: the database checks them now (PDF, JPEG, PNG or HEIC, at most
    10 MB), and the stored file is checked again when the upload completes.
    """

    child_id: UUID
    document_type: ChildDocumentType
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int

    @field_validator("filename")
    @classmethod
    def _strip_filename(cls, value: str) -> str:
        return value.strip() or "document"

    @field_validator("content_type")
    @classmethod
    def _normalise_content_type(cls, value: str) -> str:
        return value.strip().lower()


class SignedUploadResponse(BaseModel):
    """
    Post `fields` and then the file (as the last form field, named "file")
    to `url` as multipart/form-data, before `expires_at`. Then call
    complete.
    """

    url: str
    fields: dict[str, str]
    expires_at: datetime


class ChildDocumentUploadResponse(BaseModel):
    document: ChildDocumentResponse
    upload: SignedUploadResponse


class ChildDocumentDownloadResponse(BaseModel):
    """A link to view the file. It stops working at `expires_at`."""

    url: str
    expires_at: datetime
