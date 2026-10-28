import logging
import uuid

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.tenancy import (
    SiteFileInvalidError,
    SiteFileNotFoundError,
    SiteFileNotReceivedError,
    SiteIconShapeError,
)
from app.integrations.storage.client import StorageClient
from app.integrations.storage.images import check_image, prepare_photo
from app.platform.repositories.platform_site import PlatformSiteRepository
from app.platform.schemas.site import PlatformFeatureItem, PlatformSiteRequest, PlatformSiteResponse
from app.tenancy.schemas.site import SiteUploadResponse
from app.tenancy.services.site import (
    _IMAGE_TYPES,
    DOWNLOAD_EXPIRES_IN,
    MIN_ICON_PIXELS,
    PHOTO_KINDS,
    UPLOAD_EXPIRES_IN,
    _max_bytes,
    _photo,
)


logger = logging.getLogger("app.platform")


class PlatformSiteService:
    """
    The platform's landing page (docs/platform-site.md): its words, colours,
    logo and icon, photos and feature cards, changed by the platform's
    admins in place on the page (RLS checks every write) and read by anyone.
    The same rules as a business's site (app/tenancy/services/site.py),
    without policies.

    Files go straight from the browser to pending/ in the bucket, then are
    checked here and moved to their place:

        pending/platform/site/{kind}/{id}           uploading
        branding/platform/{kind}/{id}.{ext}
    """

    def __init__(
        self,
        *,
        db: Session,
        site_repository: PlatformSiteRepository,
    ):
        self.db = db
        self.site_repository = site_repository
        self.storage = StorageClient()

    def get(self) -> PlatformSiteResponse:
        site = self.site_repository.get()

        return PlatformSiteResponse(
            headline=site.headline if site else None,
            hero_text=site.hero_text if site else None,
            about_title=site.about_title if site else None,
            about=site.about if site else None,
            hero_photo=_photo(site, "hero_photo"),
            about_photo=_photo(site, "about_photo"),
            primary_color=site.primary_color if site else None,
            secondary_color=site.secondary_color if site else None,
            accent_color=site.accent_color if site else None,
            has_logo=bool(site and site.logo_key),
            has_icon=bool(site and site.icon_key),
            features=[
                PlatformFeatureItem(icon=feature.icon, title=feature.title, text=feature.description)
                for feature in self.site_repository.list_features()
            ],
        )

    @transactional
    def update(
        self,
        *,
        body: PlatformSiteRequest,
    ) -> PlatformSiteResponse:
        # Only what this editor sent.
        self.site_repository.update(values=body.model_dump(include=body.model_fields_set))
        self._log("platform_site_updated")

        return self.get()

    @transactional
    def replace_features(
        self,
        *,
        features: list[PlatformFeatureItem],
    ) -> PlatformSiteResponse:
        self.site_repository.replace_features(
            features=[(feature.icon, feature.title, feature.text) for feature in features],
        )
        self._log("platform_features_updated")

        return self.get()

    def start_upload(
        self,
        *,
        kind: str,
        content_type: str,
    ) -> SiteUploadResponse:
        """A signed upload of one file to pending/; confirm it once stored."""
        key = f"pending/platform/site/{kind}/{uuid.uuid4()}"
        signed = self.storage.create_upload(
            key=key,
            content_type=content_type,
            max_size_bytes=_max_bytes(kind),
            metadata={"kind": kind},
            expires_in=UPLOAD_EXPIRES_IN,
        )

        return SiteUploadResponse(key=key, url=signed.url, fields=signed.fields)

    @transactional
    def confirm_upload(
        self,
        *,
        kind: str,
        key: str,
    ) -> PlatformSiteResponse:
        """Check the stored file is what it should be, move it into place and use it."""
        # Only the platform's own uploads, for this kind of file.
        if not key.startswith(f"pending/platform/site/{kind}/"):
            raise SiteFileNotFoundError()

        bucket = self.storage.bucket
        stored = self.storage.get_object(bucket=bucket, key=key)

        if stored is None:
            raise SiteFileNotReceivedError()

        max_bytes = _max_bytes(kind)
        photo: bytes | None = None

        try:
            if not 1 <= stored.size_bytes <= max_bytes:
                raise SiteFileInvalidError(log_reason=f"{kind}: {stored.size_bytes} bytes")

            content = self.storage.read_start(bucket=bucket, key=key, length=max_bytes)

            if kind in PHOTO_KINDS:
                photo = prepare_photo(content)

                if photo is None:
                    raise SiteFileInvalidError(log_reason=f"{kind}: not an allowed image")

                extension = "jpg"
            else:
                image = check_image(content, allowed={"PNG"} if kind == "icon" else {"PNG", "JPEG", "WEBP"})

                if image is None:
                    raise SiteFileInvalidError(log_reason=f"{kind}: not an allowed image")

                if kind == "icon" and (image.width != image.height or image.width < MIN_ICON_PIXELS):
                    raise SiteIconShapeError(log_reason=f"icon: {image.width}x{image.height}")

                extension = image.extension
        except (SiteFileInvalidError, SiteIconShapeError):
            self.storage.delete(bucket=bucket, key=key)
            raise

        final_key = f"branding/platform/{kind}/{uuid.uuid4()}.{extension}"

        # A photo is the re-saved one; a logo or icon is the file as sent.
        if photo is not None:
            self.storage.write(bucket=bucket, key=final_key, content=photo, content_type="image/jpeg")
        else:
            self.storage.copy(bucket=bucket, source_key=key, target_key=final_key)

        self.storage.delete(bucket=bucket, key=key)
        self._replace_image(kind=kind, key=final_key)
        self._log(f"platform_{kind}_uploaded")

        return self.get()

    @transactional
    def remove_image(
        self,
        *,
        kind: str,
    ) -> PlatformSiteResponse:
        self._replace_image(kind=kind, key=None)
        self._log(f"platform_{kind}_removed")

        return self.get()

    def _replace_image(self, *, kind: str, key: str | None) -> None:
        site = self.site_repository.get()
        old_key = getattr(site, f"{kind}_key") if site else None

        values = {f"{kind}_key": key}

        # A photo taken off takes its description with it.
        if kind in PHOTO_KINDS and key is None:
            values[f"{kind}_alt"] = None

        self.site_repository.update(values=values)

        # Nothing links to the old file once replaced.
        if old_key:
            self.storage.delete(bucket=self.storage.bucket, key=old_key)

    def public_file_url(
        self,
        *,
        kind: str,
    ) -> str | None:
        """A short-lived link to the logo, icon (else the logo) or a photo, or None."""
        site = self.site_repository.get()
        key = None

        if site:
            key = (site.icon_key or site.logo_key) if kind == "icon" else getattr(site, f"{kind}_key")

        if not key:
            return None

        extension = key.rsplit(".", 1)[-1]

        return self.storage.create_download_url(
            bucket=self.storage.bucket,
            key=key,
            content_type=_IMAGE_TYPES[extension],
            filename=f"{kind}.{extension}",
            expires_in=DOWNLOAD_EXPIRES_IN,
        )

    def _log(self, event: str) -> None:
        logger.info("Platform site changed", extra={"event": event, "result": "success"})
