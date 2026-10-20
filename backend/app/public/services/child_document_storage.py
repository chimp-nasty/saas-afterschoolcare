"""
Where child documents are stored, and for how long links last. Object keys
hold only IDs (docs/child-document-retention-policy.md, section 4):

    pending/tenants/{tenant}/{document}                                    uploading
    documents/tenants/{tenant}/locations/{location}/children/{child}/{document}
"""

from datetime import timedelta
from uuid import UUID


# Matches ck_child_documents_size (schema/0004).
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024

UPLOAD_EXPIRES_IN = timedelta(minutes=15)
DOWNLOAD_EXPIRES_IN = timedelta(minutes=5)


def pending_key(
    *,
    tenant_id: UUID,
    document_id: UUID,
) -> str:
    return f"pending/tenants/{tenant_id}/{document_id}"


def document_key(
    *,
    tenant_id: UUID,
    location_id: UUID,
    child_id: UUID,
    document_id: UUID,
) -> str:
    return f"documents/tenants/{tenant_id}/locations/{location_id}/children/{child_id}/{document_id}"


def object_metadata(
    *,
    tenant_id: UUID,
    location_id: UUID,
    child_id: UUID,
    document_id: UUID,
) -> dict[str, str]:
    """IDs stored on the object, so a stray file can be traced to its owner."""
    return {
        "tenant-id": str(tenant_id),
        "location-id": str(location_id),
        "child-id": str(child_id),
        "document-id": str(document_id),
    }
