from typing import Any
from uuid import UUID

from app.db.repository import Repository
from app.db.models import Location, TenantBranding, TenantDocument, TenantFaq, TenantHighlight


class TenantSiteRepository(Repository):
    """
    The business's site (docs/tenant-administration.md, stage 5): its
    branding, FAQs and policy documents. Anyone reads them; RLS lets only
    its owner write.
    """

    def get_branding(
        self,
        *,
        tenant_id: UUID,
    ) -> TenantBranding | None:
        return (
            self.db.query(TenantBranding)
            .filter(TenantBranding.tenant_id == tenant_id)
            .first()
        )

    def save_branding(
        self,
        *,
        tenant_id: UUID,
        values: dict[str, Any],
    ) -> TenantBranding:
        """Change some of the branding, making its row the first time."""
        branding = self.get_branding(tenant_id=tenant_id)

        if branding is None:
            branding = TenantBranding(tenant_id=tenant_id)
            self.db.add(branding)

        for field, value in values.items():
            setattr(branding, field, value)

        self.db.flush()

        return branding

    def list_faqs(
        self,
        *,
        tenant_id: UUID,
    ) -> list[TenantFaq]:
        return (
            self.db.query(TenantFaq)
            .filter(TenantFaq.tenant_id == tenant_id)
            .order_by(TenantFaq.position)
            .all()
        )

    def replace_faqs(
        self,
        *,
        tenant_id: UUID,
        faqs: list[tuple[str, str]],
    ) -> list[TenantFaq]:
        """The whole list, in this order (question, answer)."""
        self.db.query(TenantFaq).filter(TenantFaq.tenant_id == tenant_id).delete()
        self.db.flush()

        records = [
            TenantFaq(tenant_id=tenant_id, position=position, question=question, answer=answer)
            for position, (question, answer) in enumerate(faqs)
        ]

        self.db.add_all(records)
        self.db.flush()

        return records

    def list_highlights(
        self,
        *,
        tenant_id: UUID,
    ) -> list[TenantHighlight]:
        return (
            self.db.query(TenantHighlight)
            .filter(TenantHighlight.tenant_id == tenant_id)
            .order_by(TenantHighlight.position)
            .all()
        )

    def replace_highlights(
        self,
        *,
        tenant_id: UUID,
        highlights: list[tuple[str, str, str]],
    ) -> list[TenantHighlight]:
        """The whole list, in this order (icon, title, description)."""
        self.db.query(TenantHighlight).filter(TenantHighlight.tenant_id == tenant_id).delete()
        self.db.flush()

        records = [
            TenantHighlight(tenant_id=tenant_id, position=position, icon=icon, title=title, description=description)
            for position, (icon, title, description) in enumerate(highlights)
        ]

        self.db.add_all(records)
        self.db.flush()

        return records

    def current_document(
        self,
        *,
        tenant_id: UUID,
        kind: str,
    ) -> TenantDocument | None:
        """The latest version of a policy."""
        return (
            self.db.query(TenantDocument)
            .filter(TenantDocument.tenant_id == tenant_id, TenantDocument.kind == kind)
            .order_by(TenantDocument.uploaded_at.desc())
            .first()
        )

    def current_document_for_location(
        self,
        *,
        location_id: UUID,
        kind: str,
    ) -> TenantDocument | None:
        """The latest version of a location's business's policy (sign-up)."""
        return (
            self.db.query(TenantDocument)
            .join(Location, Location.tenant_id == TenantDocument.tenant_id)
            .filter(Location.id == location_id, TenantDocument.kind == kind)
            .order_by(TenantDocument.uploaded_at.desc())
            .first()
        )

    def add_document(
        self,
        *,
        tenant_id: UUID,
        kind: str,
        storage_key: str,
        size_bytes: int,
        uploaded_by: UUID,
    ) -> TenantDocument:
        record = TenantDocument(
            tenant_id=tenant_id,
            kind=kind,
            storage_key=storage_key,
            size_bytes=size_bytes,
            uploaded_by=uploaded_by,
        )

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record
