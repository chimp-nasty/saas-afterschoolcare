import re
from datetime import timedelta
from functools import cache
from urllib.parse import quote

from app.core.config import settings
from app.integrations.storage.base import SignedUpload, StorageProvider, StoredObject


@cache
def _provider(name: str) -> StorageProvider:
    # Imported here so only the configured provider's SDK is loaded (and
    # its credentials looked up), once per process.
    if name == "gcs":
        from app.integrations.storage.gcs import GcsStorage

        return GcsStorage()

    from app.integrations.storage.s3 import S3Storage

    return S3Storage()


def _content_disposition(filename: str) -> str:
    """
    Open in the browser under the family's file name. The plain name is
    ASCII-only (and quote-safe) for old browsers; filename* carries the
    real one.
    """
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", filename) or "document"

    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


class StorageClient:
    """
    The app's file storage. The provider (GCS or S3) and the bucket for new
    files come from settings (STORAGE_PROVIDER, DOCUMENT_BUCKET); files
    already stored are addressed by the bucket saved with them.

    Keys are only ever built by the server and hold no personal details
    (docs/child-document-retention-policy.md, section 4).
    """

    def __init__(self):
        self._storage = _provider(settings.STORAGE_PROVIDER)

    @property
    def provider(self) -> str:
        return self._storage.name

    @property
    def bucket(self) -> str:
        return settings.DOCUMENT_BUCKET

    def create_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_size_bytes: int,
        metadata: dict[str, str],
        expires_in: timedelta,
    ) -> SignedUpload:
        """A signed browser upload of one file to `key` in the current bucket."""
        return self._storage.create_upload(
            bucket=self.bucket,
            key=key,
            content_type=content_type,
            max_size_bytes=max_size_bytes,
            metadata=metadata,
            expires_in=expires_in,
        )

    def get_object(self, *, bucket: str, key: str) -> StoredObject | None:
        return self._storage.get_object(bucket=bucket, key=key)

    def read_start(self, *, bucket: str, key: str, length: int) -> bytes:
        """The first `length` bytes, to check what kind of file it is."""
        return self._storage.read_start(bucket=bucket, key=key, length=length)

    def copy(self, *, bucket: str, source_key: str, target_key: str) -> None:
        self._storage.copy(bucket=bucket, source_key=source_key, target_key=target_key)

    def delete(self, *, bucket: str, key: str) -> None:
        self._storage.delete(bucket=bucket, key=key)

    def create_download_url(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        filename: str,
        expires_in: timedelta,
    ) -> str:
        """
        A short-lived link to view a file. The type is the one we checked
        and stored, so the browser can't be told to treat it as anything
        else.
        """
        return self._storage.create_download_url(
            bucket=bucket,
            key=key,
            content_type=content_type,
            content_disposition=_content_disposition(filename),
            expires_in=expires_in,
        )
