import logging
import uuid
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache.stores import cache_stores
from app.db.transaction import transactional
from app.errors.tenancy import (
    SiteFileInvalidError,
    SiteFileNotFoundError,
    SiteFileNotReceivedError,
    SiteIconShapeError,
)
from app.integrations.storage.client import StorageClient
from app.integrations.storage.images import check_image
from app.tenancy.repositories.tenant import TenantRepository
from app.tenancy.repositories.tenant_site import TenantSiteRepository
from app.tenancy.schemas.site import (
    FaqItem,
    HighlightItem,
    PublicBusinessResponse,
    PublicFaqResponse,
    SiteDocumentResponse,
    SiteRequest,
    SiteResponse,
    SiteUploadResponse,
)


logger = logging.getLogger("app.tenancy")

# Upload limits (ck_tenant_documents_size for policies).
MAX_IMAGE_BYTES = 1024 * 1024
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MIN_ICON_PIXELS = 192

UPLOAD_EXPIRES_IN = timedelta(minutes=15)
# Links the public pages follow (logo, icon, policies): long enough for a
# page to load them, short enough not to be shared.
DOWNLOAD_EXPIRES_IN = timedelta(hours=1)

IMAGE_KINDS = {"logo", "icon"}
DOCUMENT_KINDS = {"privacy", "terms"}

_IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}
_DOCUMENT_NAMES = {"privacy": "Privacy policy.pdf", "terms": "Terms.pdf"}


class SiteService:
    """
    The business's site (docs/tenant-administration.md, stage 5): its
    landing page's headline, colours, logo and icon, FAQs and policy PDFs.
    The owner changes them in Business settings › Your site (RLS checks the
    tenant permission on every write); anyone reads them.

    Files go straight from the browser to pending/ in the bucket, then are
    checked here (what they really are, their size, an icon's shape) and
    moved to their place. Object keys hold only IDs:

        pending/tenants/{tenant}/site/{kind}/{id}           uploading
        branding/tenants/{tenant}/{logo|icon}/{id}.{ext}
        policies/tenants/{tenant}/{privacy|terms}/{id}.pdf
    """

    def __init__(
        self,
        *,
        db: Session,
        tenant_repository: TenantRepository,
        site_repository: TenantSiteRepository,
    ):
        self.db = db
        self.tenant_repository = tenant_repository
        self.site_repository = site_repository
        self.storage = StorageClient()

    # ------------------------------------------------------------------
    # Business settings › Your site
    # ------------------------------------------------------------------

    def get_site(
        self,
        *,
        tenant_id: UUID,
    ) -> SiteResponse:
        tenant = self.tenant_repository.get_by_id(id=tenant_id)
        branding = self.site_repository.get_branding(tenant_id=tenant_id)

        documents = [
            SiteDocumentResponse(kind=kind, uploaded_at=document.uploaded_at)
            for kind in sorted(DOCUMENT_KINDS)
            if (document := self.site_repository.current_document(tenant_id=tenant_id, kind=kind))
        ]

        return SiteResponse(
            tagline=tenant.tagline,
            hero_text=tenant.hero_text,
            primary_color=branding.primary_color if branding else None,
            secondary_color=branding.secondary_color if branding else None,
            accent_color=branding.accent_color if branding else None,
            has_logo=bool(branding and branding.logo_key),
            has_icon=bool(branding and branding.icon_key),
            documents=documents,
            faqs=[
                FaqItem(question=faq.question, answer=faq.answer)
                for faq in self.site_repository.list_faqs(tenant_id=tenant_id)
            ],
            highlights=self._highlights(tenant_id),
        )

    def _highlights(self, tenant_id: UUID) -> list[HighlightItem]:
        return [
            HighlightItem(icon=highlight.icon, title=highlight.title, text=highlight.description)
            for highlight in self.site_repository.list_highlights(tenant_id=tenant_id)
        ]

    @transactional
    def update_site(
        self,
        *,
        tenant_id: UUID,
        body: SiteRequest,
    ) -> SiteResponse:
        tenant = self.tenant_repository.get_by_id(id=tenant_id)

        # Only what this editor sent (SiteRequest).
        sent = body.model_dump(include=body.model_fields_set)
        words = {field: sent[field] for field in ("tagline", "hero_text", "about") if field in sent}
        colours = {
            field: sent[field] for field in ("primary_color", "secondary_color", "accent_color") if field in sent
        }

        if words:
            self.tenant_repository.update(tenant=tenant, values=words)

        if colours:
            self.site_repository.save_branding(tenant_id=tenant_id, values=colours)
            self._branding_changed()

        self._log("site_updated", tenant_id)

        return self.get_site(tenant_id=tenant_id)

    @transactional
    def replace_faqs(
        self,
        *,
        tenant_id: UUID,
        faqs: list[FaqItem],
    ) -> SiteResponse:
        self.site_repository.replace_faqs(
            tenant_id=tenant_id,
            faqs=[(faq.question, faq.answer) for faq in faqs],
        )
        self._log("faqs_updated", tenant_id)

        return self.get_site(tenant_id=tenant_id)

    @transactional
    def replace_highlights(
        self,
        *,
        tenant_id: UUID,
        highlights: list[HighlightItem],
    ) -> SiteResponse:
        self.site_repository.replace_highlights(
            tenant_id=tenant_id,
            highlights=[(highlight.icon, highlight.title, highlight.text) for highlight in highlights],
        )
        self._log("highlights_updated", tenant_id)

        return self.get_site(tenant_id=tenant_id)

    def start_upload(
        self,
        *,
        tenant_id: UUID,
        kind: str,
        content_type: str,
    ) -> SiteUploadResponse:
        """A signed upload of one file to pending/; confirm it once stored."""
        is_document = kind in DOCUMENT_KINDS

        if is_document != (content_type == "application/pdf"):
            raise SiteFileInvalidError()

        key = f"pending/tenants/{tenant_id}/site/{kind}/{uuid.uuid4()}"
        signed = self.storage.create_upload(
            key=key,
            content_type=content_type,
            max_size_bytes=MAX_DOCUMENT_BYTES if is_document else MAX_IMAGE_BYTES,
            metadata={"tenant-id": str(tenant_id), "kind": kind},
            expires_in=UPLOAD_EXPIRES_IN,
        )

        return SiteUploadResponse(key=key, url=signed.url, fields=signed.fields)

    @transactional
    def confirm_upload(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        kind: str,
        key: str,
    ) -> SiteResponse:
        """
        Check the stored file is what it should be, move it into place and
        use it: a logo or icon replaces the old one; a policy adds a new
        version (the old ones stay, for what families accepted).
        """
        # Only this business's own uploads, for this kind of file.
        if not key.startswith(f"pending/tenants/{tenant_id}/site/{kind}/"):
            raise SiteFileNotFoundError()

        bucket = self.storage.bucket
        stored = self.storage.get_object(bucket=bucket, key=key)

        if stored is None:
            raise SiteFileNotReceivedError()

        is_document = kind in DOCUMENT_KINDS
        max_bytes = MAX_DOCUMENT_BYTES if is_document else MAX_IMAGE_BYTES

        try:
            if not 1 <= stored.size_bytes <= max_bytes:
                raise SiteFileInvalidError(log_reason=f"{kind}: {stored.size_bytes} bytes")

            content = self.storage.read_start(bucket=bucket, key=key, length=max_bytes)

            if is_document:
                if not content.startswith(b"%PDF-"):
                    raise SiteFileInvalidError(log_reason=f"{kind}: not a PDF")

                extension = "pdf"
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

        folder = "policies" if is_document else "branding"
        final_key = f"{folder}/tenants/{tenant_id}/{kind}/{uuid.uuid4()}.{extension}"

        self.storage.copy(bucket=bucket, source_key=key, target_key=final_key)
        self.storage.delete(bucket=bucket, key=key)

        if is_document:
            self.site_repository.add_document(
                tenant_id=tenant_id,
                kind=kind,
                storage_key=final_key,
                size_bytes=stored.size_bytes,
                uploaded_by=user_id,
            )
        else:
            self._replace_image(tenant_id=tenant_id, kind=kind, key=final_key)

        self._log(f"{kind}_uploaded", tenant_id)

        return self.get_site(tenant_id=tenant_id)

    @transactional
    def remove_image(
        self,
        *,
        tenant_id: UUID,
        kind: str,
    ) -> SiteResponse:
        """The logo or icon taken off (policies are only ever replaced)."""
        self._replace_image(tenant_id=tenant_id, kind=kind, key=None)
        self._log(f"{kind}_removed", tenant_id)

        return self.get_site(tenant_id=tenant_id)

    def _replace_image(self, *, tenant_id: UUID, kind: str, key: str | None) -> None:
        branding = self.site_repository.get_branding(tenant_id=tenant_id)
        old_key = getattr(branding, f"{kind}_key") if branding else None

        self.site_repository.save_branding(tenant_id=tenant_id, values={f"{kind}_key": key})
        self._branding_changed()

        # Nothing links to the old file once replaced.
        if old_key:
            self.storage.delete(bucket=self.storage.bucket, key=old_key)

    # ------------------------------------------------------------------
    # The public landing page
    # ------------------------------------------------------------------

    def public_business(
        self,
        *,
        tenant_id: UUID,
    ) -> PublicBusinessResponse:
        tenant = self.tenant_repository.get_by_id(id=tenant_id)
        branding = self.site_repository.get_branding(tenant_id=tenant_id)

        return PublicBusinessResponse(
            name=tenant.name,
            tagline=tenant.tagline,
            hero_text=tenant.hero_text,
            about=tenant.about,
            email=tenant.email,
            phone=tenant.phone,
            primary_color=branding.primary_color if branding else None,
            secondary_color=branding.secondary_color if branding else None,
            accent_color=branding.accent_color if branding else None,
            has_logo=bool(branding and branding.logo_key),
            has_privacy=self.site_repository.current_document(tenant_id=tenant_id, kind="privacy") is not None,
            has_terms=self.site_repository.current_document(tenant_id=tenant_id, kind="terms") is not None,
            faqs=[
                PublicFaqResponse(question=faq.question, answer=faq.answer)
                for faq in self.site_repository.list_faqs(tenant_id=tenant_id)
            ],
            highlights=self._highlights(tenant_id),
        )

    def public_file_url(
        self,
        *,
        tenant_id: UUID,
        kind: str,
    ) -> str | None:
        """
        A short-lived link to the business's logo, icon (else its logo) or
        current policy, or None when it has none.
        """
        if kind in DOCUMENT_KINDS:
            document = self.site_repository.current_document(tenant_id=tenant_id, kind=kind)

            if not document:
                return None

            key, content_type, filename = document.storage_key, "application/pdf", _DOCUMENT_NAMES[kind]
        else:
            branding = self.site_repository.get_branding(tenant_id=tenant_id)
            key = None

            if branding:
                key = (branding.icon_key or branding.logo_key) if kind == "icon" else branding.logo_key

            if not key:
                return None

            extension = key.rsplit(".", 1)[-1]
            content_type, filename = _IMAGE_TYPES[extension], f"{kind}.{extension}"

        return self.storage.create_download_url(
            bucket=self.storage.bucket,
            key=key,
            content_type=content_type,
            filename=filename,
            expires_in=DOWNLOAD_EXPIRES_IN,
        )

    def _branding_changed(self) -> None:
        """
        Centre pages cache their location (colours included) for a few
        minutes; show the business's new branding straight away (this
        process's cache).
        """
        cache_stores.location_branding.clear()

    def _log(self, event: str, tenant_id: UUID) -> None:
        logger.info(
            "Business site changed",
            extra={"event": event, "result": "success", "reason": f"tenant_id={tenant_id}"},
        )
