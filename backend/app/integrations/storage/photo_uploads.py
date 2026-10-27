"""
Photos for the public site (docs/public-site.md, stage 9b: a centre's and a
program's), uploaded the same way as the business's own: straight from the
browser to pending/, then checked and re-saved here (images.prepare_photo:
a JPEG without its metadata) under their final key. Object keys hold only
IDs. The caller decides who may, and stores and removes the key.
"""

import uuid
from datetime import timedelta

from app.errors.tenancy import SiteFileInvalidError, SiteFileNotFoundError, SiteFileNotReceivedError
from app.integrations.storage.client import StorageClient
from app.integrations.storage.images import prepare_photo


MAX_PHOTO_BYTES = 8 * 1024 * 1024
UPLOAD_EXPIRES_IN = timedelta(minutes=15)
# Links the public pages follow: long enough for a page, short enough not
# to be shared.
DOWNLOAD_EXPIRES_IN = timedelta(hours=1)


class PhotoUploads:
    def __init__(self, storage: StorageClient):
        self.storage = storage

    def start(self, *, pending_prefix: str, content_type: str, metadata: dict[str, str]) -> tuple[str, str, dict]:
        """A signed upload to pending_prefix/{id}: (key, url, fields)."""
        key = f"{pending_prefix}/{uuid.uuid4()}"
        signed = self.storage.create_upload(
            key=key,
            content_type=content_type,
            max_size_bytes=MAX_PHOTO_BYTES,
            metadata=metadata,
            expires_in=UPLOAD_EXPIRES_IN,
        )

        return key, signed.url, signed.fields

    def confirm(self, *, key: str, pending_prefix: str, final_prefix: str) -> str:
        """
        Check the uploaded file is a photo, re-save it as final_prefix/{id}.jpg
        and drop the upload; that new key. Anything else is refused and
        deleted.
        """
        # Only uploads started for this photo.
        if not key.startswith(f"{pending_prefix}/"):
            raise SiteFileNotFoundError()

        bucket = self.storage.bucket
        stored = self.storage.get_object(bucket=bucket, key=key)

        if stored is None:
            raise SiteFileNotReceivedError()

        try:
            if not 1 <= stored.size_bytes <= MAX_PHOTO_BYTES:
                raise SiteFileInvalidError(log_reason=f"photo: {stored.size_bytes} bytes")

            photo = prepare_photo(self.storage.read_start(bucket=bucket, key=key, length=MAX_PHOTO_BYTES))

            if photo is None:
                raise SiteFileInvalidError(log_reason="photo: not an allowed image")
        except SiteFileInvalidError:
            self.storage.delete(bucket=bucket, key=key)
            raise

        final_key = f"{final_prefix}/{uuid.uuid4()}.jpg"

        self.storage.write(bucket=bucket, key=final_key, content=photo, content_type="image/jpeg")
        self.storage.delete(bucket=bucket, key=key)

        return final_key

    def remove(self, key: str | None) -> None:
        """A replaced or removed photo's file: nothing links to it any more."""
        if key:
            self.storage.delete(bucket=self.storage.bucket, key=key)

    def download_url(self, key: str) -> str:
        return self.storage.create_download_url(
            bucket=self.storage.bucket,
            key=key,
            content_type="image/jpeg",
            filename="photo.jpg",
            expires_in=DOWNLOAD_EXPIRES_IN,
        )


def photo_version(key: str) -> str:
    """A photo's file id: new with every upload (for ?v= on its link)."""
    return key.rsplit("/", 1)[-1].split(".", 1)[0]
