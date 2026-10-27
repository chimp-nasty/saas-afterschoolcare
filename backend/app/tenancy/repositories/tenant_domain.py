from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text

from app.db.models import Tenant, TenantCertificate, TenantDomain
from app.db.repository import Repository


# Proven domains: on the business's certificate (schema/0002).
PROVEN_STATES = ("verified", "active", "suspended")


class TenantDomainRepository(Repository):
    """
    Custom domains and their certificates (schema/0002). The owner sees,
    adds and removes its business's domains; the domain check (RLS channel
    domain_check) sees and moves every business's.
    """

    def now(self) -> datetime:
        """The database's clock: every domain timestamp is compared with it."""
        return self.db.execute(select(func.now())).scalar_one()

    def lock(self) -> None:
        """
        One domain check at a time (the scheduler and an owner's "Check now"),
        so the load balancer is only ever changed by one; held until the
        transaction ends.
        """
        self.db.execute(text("SELECT pg_advisory_xact_lock(hashtext('tenancy.domain_check'))"))

    # ------------------------------------------------------------------
    # Domains
    # ------------------------------------------------------------------

    def list_for_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> list[TenantDomain]:
        """Main domain first, then the rest as they were added."""
        return (
            self.db.query(TenantDomain)
            .filter(TenantDomain.tenant_id == tenant_id)
            .order_by(TenantDomain.is_main.desc(), TenantDomain.created_at)
            .all()
        )

    def get(
        self,
        *,
        tenant_id: UUID,
        id: UUID,
    ) -> TenantDomain | None:
        return (
            self.db.query(TenantDomain)
            .filter(TenantDomain.tenant_id == tenant_id, TenantDomain.id == id)
            .first()
        )

    def add(
        self,
        *,
        values: dict[str, Any],
    ) -> TenantDomain:
        domain = TenantDomain(**values)

        self.db.add(domain)
        self.db.flush()

        return domain

    def update(
        self,
        *,
        domain: TenantDomain,
        values: dict[str, Any],
    ) -> TenantDomain:
        for field, value in values.items():
            setattr(domain, field, value)

        self.db.flush()

        return domain

    def delete(
        self,
        *,
        domain: TenantDomain,
    ) -> None:
        self.db.delete(domain)
        self.db.flush()

    def proven_by_another(
        self,
        *,
        tenant_id: UUID,
        hostname: str,
    ) -> bool:
        """Another business has already proven this domain (domain check only)."""
        return self.db.query(
            self.db.query(TenantDomain)
            .filter(
                TenantDomain.hostname == hostname,
                TenantDomain.tenant_id != tenant_id,
                TenantDomain.state.in_(PROVEN_STATES + ("removing",)),
            )
            .exists()
        ).scalar()

    def tenants_with_domains(self) -> list[UUID]:
        """Every business with a domain or a certificate (domain check only)."""
        domains = select(TenantDomain.tenant_id)
        certificates = select(TenantCertificate.tenant_id)

        return list(self.db.execute(domains.union(certificates)).scalars())

    def cloud_names(self) -> tuple[set[str], set[str]]:
        """
        Every certificate and DNS authorization the database knows (domain
        check only), as (certificate names, authorization names): anything
        else of ours at Google is an orphan.
        """
        certificates = set(self.db.execute(select(TenantCertificate.name)).scalars())
        authorizations = {
            name
            for row in self.db.execute(select(TenantDomain.dns_authorization, TenantDomain.www_dns_authorization))
            for name in row
            if name
        }

        return certificates, authorizations

    def live_sites(self) -> list[tuple[Tenant, list[TenantDomain]]]:
        """
        Every business whose main domain is live, with its live domains
        (domain check only): what the load balancer's redirects are built
        from.
        """
        tenants = (
            self.db.query(Tenant)
            .filter(Tenant.custom_domain.isnot(None))
            .order_by(Tenant.code)
            .all()
        )

        return [
            (
                tenant,
                self.db.query(TenantDomain)
                .filter(TenantDomain.tenant_id == tenant.id, TenantDomain.state == "active")
                .all(),
            )
            for tenant in tenants
        ]

    # ------------------------------------------------------------------
    # Certificates (domain check only)
    # ------------------------------------------------------------------

    def certificates_for_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> list[TenantCertificate]:
        """Newest first."""
        return (
            self.db.query(TenantCertificate)
            .filter(TenantCertificate.tenant_id == tenant_id)
            .order_by(TenantCertificate.created_at.desc())
            .all()
        )

    def certificates_in_state(
        self,
        *,
        state: str,
    ) -> list[TenantCertificate]:
        return (
            self.db.query(TenantCertificate)
            .filter(TenantCertificate.state == state)
            .order_by(TenantCertificate.name)
            .all()
        )

    def add_certificate(
        self,
        *,
        values: dict[str, Any],
    ) -> TenantCertificate:
        certificate = TenantCertificate(**values)

        self.db.add(certificate)
        self.db.flush()

        return certificate

    def update_certificate(
        self,
        *,
        certificate: TenantCertificate,
        values: dict[str, Any],
    ) -> TenantCertificate:
        for field, value in values.items():
            setattr(certificate, field, value)

        self.db.flush()

        return certificate

    def delete_certificate(
        self,
        *,
        certificate: TenantCertificate,
    ) -> None:
        self.db.delete(certificate)
        self.db.flush()
