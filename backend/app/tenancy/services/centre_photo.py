import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache.stores import cache_stores
from app.db.transaction import transactional
from app.errors.tenancy import LocationNotFoundError
from app.integrations.storage.client import StorageClient
from app.integrations.storage.photo_uploads import PhotoUploads, photo_version
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.schemas.site import PhotoResponse, SiteUploadResponse


logger = logging.getLogger("app.tenancy")


def centre_photo(location) -> PhotoResponse | None:
    """A centre's photo, as its pages show it, or None."""
    if not location.photo_key:
        return None

    return PhotoResponse(version=photo_version(location.photo_key), alt=location.photo_alt)


class CentrePhotoService:
    """
    A centre's photo (docs/public-site.md, stage 9b): its page's hero (in
    place of the business's) and its card on /locations. The business's
    owner sets it, inline on the centre's page, like the centre's other
    details (tenant_locations u; RLS checks it on the write). Keys:

        pending/locations/{location}/photo/{id}       uploading
        branding/locations/{location}/photo/{id}.jpg
    """

    def __init__(
        self,
        *,
        db: Session,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.location_repository = location_repository
        self.photos = PhotoUploads(StorageClient())

    def _location(self, *, tenant_id: UUID, location_id: UUID):
        location = self.location_repository.get_by_id(id=location_id)

        if not location or location.tenant_id != tenant_id:
            raise LocationNotFoundError()

        return location

    def start_upload(self, *, tenant_id: UUID, location_id: UUID, content_type: str) -> SiteUploadResponse:
        self._location(tenant_id=tenant_id, location_id=location_id)

        key, url, fields = self.photos.start(
            pending_prefix=f"pending/locations/{location_id}/photo",
            content_type=content_type,
            metadata={"tenant-id": str(tenant_id), "location-id": str(location_id), "kind": "centre-photo"},
        )

        return SiteUploadResponse(key=key, url=url, fields=fields)

    @transactional
    def confirm_upload(self, *, tenant_id: UUID, location_id: UUID, key: str) -> PhotoResponse | None:
        """The uploaded photo, checked and re-saved, in place of any before."""
        location = self._location(tenant_id=tenant_id, location_id=location_id)

        final_key = self.photos.confirm(
            key=key,
            pending_prefix=f"pending/locations/{location_id}/photo",
            final_prefix=f"branding/locations/{location_id}/photo",
        )

        return self._replace(location=location, values={"photo_key": final_key}, event="centre_photo_uploaded")

    @transactional
    def remove(self, *, tenant_id: UUID, location_id: UUID) -> PhotoResponse | None:
        """Taken off, with its description: the page uses the business's again."""
        location = self._location(tenant_id=tenant_id, location_id=location_id)

        return self._replace(
            location=location, values={"photo_key": None, "photo_alt": None}, event="centre_photo_removed"
        )

    @transactional
    def update_alt(self, *, tenant_id: UUID, location_id: UUID, alt: str | None) -> PhotoResponse | None:
        location = self._location(tenant_id=tenant_id, location_id=location_id)

        self.location_repository.update(location=location, values={"photo_alt": alt})
        self._changed(location)

        return centre_photo(location)

    def public_url(self, *, location_id: UUID) -> str | None:
        """A short-lived link to the centre's photo, or None when it has none."""
        location = self.location_repository.get_by_id(id=location_id)

        return self.photos.download_url(location.photo_key) if location and location.photo_key else None

    def _replace(self, *, location, values: dict, event: str) -> PhotoResponse | None:
        old_key = location.photo_key

        self.location_repository.update(location=location, values=values)
        self._changed(location)

        if old_key and old_key != location.photo_key:
            self.photos.remove(old_key)

        logger.info(
            "Centre photo changed",
            extra={"event": event, "result": "success", "reason": f"location_id={location.id}"},
        )

        return centre_photo(location)

    def _changed(self, location) -> None:
        # The public page caches a location for a few minutes; show the
        # change straight away (this process's cache).
        cache_stores.location_branding.pop(location.id, None)
