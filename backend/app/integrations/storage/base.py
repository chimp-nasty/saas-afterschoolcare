from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class SignedUpload:
    """
    A browser upload straight to the provider: an HTML form POST of
    `fields` plus the file (as the last field, named "file") to `url`. The
    provider itself enforces the policy (object key, content type, size).
    """

    url: str
    fields: dict[str, str]


@dataclass
class StoredObject:
    size_bytes: int
    content_type: str | None


class StorageProvider(ABC):
    """
    What the app needs from an object store. One implementation per provider
    (GCS, S3); StorageClient picks one from settings, and services only ever
    see StorageClient.
    """

    name: str

    @abstractmethod
    def create_upload(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        max_size_bytes: int,
        metadata: dict[str, str],
        expires_in: timedelta,
    ) -> SignedUpload: ...

    @abstractmethod
    def get_object(
        self,
        *,
        bucket: str,
        key: str,
    ) -> StoredObject | None: ...

    @abstractmethod
    def read_start(
        self,
        *,
        bucket: str,
        key: str,
        length: int,
    ) -> bytes: ...

    @abstractmethod
    def copy(
        self,
        *,
        bucket: str,
        source_key: str,
        target_key: str,
    ) -> None: ...

    @abstractmethod
    def write(
        self,
        *,
        bucket: str,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        """Store bytes the API made itself (e.g. a re-saved photo)."""

    @abstractmethod
    def delete(
        self,
        *,
        bucket: str,
        key: str,
    ) -> None:
        """Delete an object; an object that's already gone is fine."""

    @abstractmethod
    def create_download_url(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        content_disposition: str,
        expires_in: timedelta,
    ) -> str: ...
