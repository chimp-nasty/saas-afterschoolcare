import logging
import uuid
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.core.cache.stores import cache_stores
from app.core.config import settings
from app.db.models import TenantCertificate, TenantDomain
from app.db.transaction import transactional
from app.integrations.domains.base import SiteRedirect
from app.integrations.domains.client import DomainsClient
from app.tenancy.repositories.tenant import TenantRepository
from app.tenancy.repositories.tenant_domain import PROVEN_STATES, TenantDomainRepository


logger = logging.getLogger("app.domains")

# A domain whose records aren't found in this long is given up.
PENDING_DAYS = 7
# Live domains are looked up again once a day; this many failed lookups in
# a row suspend one (the generated host takes over until they return).
LIVE_CHECK_INTERVAL = timedelta(days=1)
SUSPEND_AFTER_FAILED_CHECKS = 3


def domain_hostnames(domain: TenantDomain) -> list[str]:
    """The hostnames a domain covers: itself, and www when chosen."""
    return [domain.hostname, f"www.{domain.hostname}"] if domain.include_www else [domain.hostname]


def verify_record_name(hostname: str) -> str:
    """The TXT record proving which business owns a domain."""
    return f"{settings.DOMAINS_VERIFY_LABEL}.{hostname}"


class DomainCheckService:
    """
    Moves every business's custom domains along (docs/tenant-administration.md,
    section 7; the states are described in schema/0002). Cloud Scheduler
    calls it every 5 minutes; an owner's "Check now" and removing a domain
    run it for their business at once.

    Server code with no user: its transactions use the domain_check RLS
    channel, which sees every business's domains. One business per
    transaction, one check at a time (an advisory lock), then the load
    balancer is brought in line with the database:

    1. Domains: look up the owner's records. A pending domain is proven by
       its TXT record and certificate CNAME; a live one is checked daily.
    2. The business's certificate: one covering all its proven domains. When
       the set changes a new one is issued; the old one serves until the new
       one is on the load balancer, then it's retired.
    3. A proven domain goes live once its certificate is on the load balancer
       and it points at us; the live main domain is tenants.custom_domain.
    4. Removed domains go once no certificate covers them.
    5. The load balancer: every business's current certificates and
       redirects, then retired certificates are deleted.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        domain_repository: TenantDomainRepository,
        tenant_repository: TenantRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.domain_repository = domain_repository
        self.tenant_repository = tenant_repository
        self.domains = DomainsClient()

    def check_all(self) -> int:
        """The scheduled check: every business with domains. Returns how many."""
        tenant_ids = self._tenants_with_domains()

        for tenant_id in tenant_ids:
            # One business's trouble (Google refusing something) doesn't
            # hold up the others; it's tried again next time.
            try:
                self._check_tenant(tenant_id=tenant_id, force=False)
            except Exception:
                logger.exception(
                    "Domain check failed for a business",
                    extra={"event": "domain_check", "result": "failed", "reason": f"tenant={tenant_id}"},
                )

        self._apply_routing()

        return len(tenant_ids)

    def check_tenant(
        self,
        *,
        tenant_id: UUID,
        passes: int = 3,
    ) -> None:
        """
        One business now (its owner pressed Check now, or removed a domain),
        including its live domains' daily lookups. A few passes, so steps
        that are already done (a certificate Google has issued) are taken at
        once rather than on the next scheduled check.
        """
        for index in range(passes):
            changed = self._check_tenant(tenant_id=tenant_id, force=index == 0)
            changed = self._apply_routing() or changed

            if not changed:
                break

    # ------------------------------------------------------------------
    # One business
    # ------------------------------------------------------------------

    @transactional
    def _tenants_with_domains(self) -> list[UUID]:
        self._begin()

        return self.domain_repository.tenants_with_domains()

    def _begin(self) -> None:
        self.rls_context.set_domain_check_channel()
        self.domain_repository.lock()

    @transactional
    def _check_tenant(
        self,
        *,
        tenant_id: UUID,
        force: bool,
    ) -> bool:
        """Returns whether anything changed."""
        self._begin()

        now = self.domain_repository.now()
        domains = self.domain_repository.list_for_tenant(tenant_id=tenant_id)
        before = self._snapshot(tenant_id, domains)

        for domain in domains:
            self._check_records(domain=domain, now=now, force=force)

        certificate = self._certificate(tenant_id=tenant_id, domains=domains, force=force)
        attached = bool(certificate and certificate.state == "active" and certificate.attached_at)

        for domain in domains:
            if domain.state == "verified" and attached and self._points_to_us(domain):
                self.domain_repository.update(
                    domain=domain,
                    values={"state": "active", "active_at": now, "failed_checks": 0},
                )

                logger.info(
                    "Custom domain live",
                    extra={"event": "domain_live", "result": "success", "reason": f"domain={domain.id}"},
                )

        self._set_main_domain(tenant_id=tenant_id, domains=domains)
        self._clean_up_removed(tenant_id=tenant_id, domains=domains)

        return before != self._snapshot(tenant_id, self.domain_repository.list_for_tenant(tenant_id=tenant_id))

    def _snapshot(self, tenant_id: UUID, domains: list[TenantDomain]):
        certificates = self.domain_repository.certificates_for_tenant(tenant_id=tenant_id)

        return (
            sorted((str(d.id), d.state) for d in domains),
            sorted((c.name, c.state, c.attached_at is not None) for c in certificates),
        )

    def _check_records(
        self,
        *,
        domain: TenantDomain,
        now: datetime,
        force: bool,
    ) -> None:
        if domain.state == "pending_dns":
            if now - domain.created_at > timedelta(days=PENDING_DAYS):
                self.domain_repository.update(
                    domain=domain,
                    values={
                        "state": "failed",
                        "failure_reason": f"Its DNS records weren't found within {PENDING_DAYS} days.",
                    },
                )
                return

            self._look_up(domain=domain, now=now)

            if not self._proven(domain):
                return

            if self.domain_repository.proven_by_another(tenant_id=domain.tenant_id, hostname=domain.hostname):
                self.domain_repository.update(
                    domain=domain,
                    values={"failure_reason": "Another business has already set up this domain."},
                )
                return

            self.domain_repository.update(
                domain=domain,
                values={"state": "verified", "verified_at": now, "failure_reason": None},
            )
            return

        if domain.state == "verified":
            self._look_up(domain=domain, now=now)
            return

        if domain.state in ("active", "suspended"):
            due = domain.last_checked_at is None or now - domain.last_checked_at >= LIVE_CHECK_INTERVAL

            if not (force or due):
                return

            self._look_up(domain=domain, now=now)

            if self._proven(domain) and self._points_to_us(domain):
                self.domain_repository.update(
                    domain=domain,
                    values={"state": "active", "failed_checks": 0, "failure_reason": None},
                )
                return

            failed_checks = domain.failed_checks + 1
            suspend = failed_checks >= SUSPEND_AFTER_FAILED_CHECKS
            newly_suspended = suspend and domain.state == "active"

            self.domain_repository.update(
                domain=domain,
                values={
                    "failed_checks": failed_checks,
                    "state": "suspended" if suspend else domain.state,
                    "failure_reason": "Its DNS records are missing or changed." if suspend else domain.failure_reason,
                },
            )

            if newly_suspended:
                logger.warning(
                    "Custom domain suspended",
                    extra={"event": "domain_suspended", "result": "failed", "reason": f"domain={domain.id}"},
                )

    def _look_up(
        self,
        *,
        domain: TenantDomain,
        now: datetime,
    ) -> None:
        address = settings.DOMAINS_TARGET_IP or ""
        www = f"www.{domain.hostname}"

        values = {
            "last_checked_at": now,
            "txt_seen": self.domains.has_txt(
                name=verify_record_name(domain.hostname),
                value=domain.verification_token,
            ),
            "auth_seen": self.domains.has_cname(name=domain.auth_record_name, target=domain.auth_record_value),
            "address_seen": self.domains.points_to(name=domain.hostname, address=address),
        }

        if domain.include_www:
            values["www_auth_seen"] = self.domains.has_cname(
                name=domain.www_auth_record_name,
                target=domain.www_auth_record_value,
            )
            values["www_address_seen"] = self.domains.points_to(name=www, address=address)

        self.domain_repository.update(domain=domain, values=values)

    @staticmethod
    def _proven(domain: TenantDomain) -> bool:
        """The business owns it, and Google may issue its certificate."""
        return domain.txt_seen and domain.auth_seen and (domain.www_auth_seen or not domain.include_www)

    @staticmethod
    def _points_to_us(domain: TenantDomain) -> bool:
        return domain.address_seen and (domain.www_address_seen or not domain.include_www)

    def _certificate(
        self,
        *,
        tenant_id: UUID,
        domains: list[TenantDomain],
        force: bool,
    ) -> TenantCertificate | None:
        """
        The business's certificate for its proven domains, issuing one when
        there isn't one, and retiring the rest once it's on the load balancer.
        """
        proven = [domain for domain in domains if domain.state in PROVEN_STATES]
        wanted = ",".join(sorted(hostname for domain in proven for hostname in domain_hostnames(domain)))
        certificates = self.domain_repository.certificates_for_tenant(tenant_id=tenant_id)

        for certificate in certificates:
            if certificate.state == "issuing":
                status = self.domains.certificate_status(name=certificate.name)

                if status.state != "issuing":
                    self.domain_repository.update_certificate(
                        certificate=certificate,
                        values={"state": status.state, "failure_reason": status.reason},
                    )

        current = next(
            (c for c in certificates if c.hostnames == wanted and c.state in ("issuing", "active")),
            None,
        )
        failed = next((c for c in certificates if c.hostnames == wanted and c.state == "failed"), None)

        if wanted and current is None and failed is not None and not force:
            # Google couldn't issue it: the domains waiting on it fail (the
            # live ones keep their certificate), so the next set differs.
            for domain in proven:
                if domain.state == "verified":
                    self.domain_repository.update(
                        domain=domain,
                        values={
                            "state": "failed",
                            "failure_reason": f"Its certificate couldn't be issued: {failed.failure_reason}",
                        },
                    )

            return None

        if wanted and current is None:
            name = f"t-{tenant_id.hex[:12]}-{uuid.uuid4().hex[:8]}"

            self.domains.create_certificate(
                name=name,
                hostnames=wanted.split(","),
                dns_authorizations=[
                    authorization
                    for domain in proven
                    for authorization in (domain.dns_authorization, domain.www_dns_authorization)
                    if authorization
                ],
            )

            current = self.domain_repository.add_certificate(
                values={"tenant_id": tenant_id, "name": name, "hostnames": wanted, "state": "issuing"},
            )

            logger.info(
                "Certificate requested",
                extra={"event": "domain_certificate_requested", "result": "success", "reason": f"certificate={name}"},
            )

        # Once the current one is serving (or nothing is wanted), the others go.
        if not wanted or (current.state == "active" and current.attached_at):
            for certificate in certificates:
                if certificate is not current and certificate.state != "retiring":
                    self.domain_repository.update_certificate(certificate=certificate, values={"state": "retiring"})

        return current

    def _set_main_domain(
        self,
        *,
        tenant_id: UUID,
        domains: list[TenantDomain],
    ) -> None:
        """The live main domain is where the business's site lives."""
        live = next((d.hostname for d in domains if d.is_main and d.state == "active"), None)
        tenant = self.tenant_repository.get_by_id(id=tenant_id)

        if tenant.custom_domain != live:
            self.tenant_repository.update(tenant=tenant, values={"custom_domain": live})
            # The landing page names its main host.
            cache_stores.location_branding.clear()

            logger.info(
                "Main domain changed",
                extra={"event": "domain_main_changed", "result": "success", "reason": f"tenant={tenant_id}; live={bool(live)}"},
            )

    def _clean_up_removed(
        self,
        *,
        tenant_id: UUID,
        domains: list[TenantDomain],
    ) -> None:
        """Removed domains go once no certificate covers them any more."""
        covered = {
            hostname
            for certificate in self.domain_repository.certificates_for_tenant(tenant_id=tenant_id)
            for hostname in certificate.hostnames.split(",")
        }

        for domain in domains:
            if domain.state != "removing" or covered.intersection(domain_hostnames(domain)):
                continue

            for authorization in (domain.dns_authorization, domain.www_dns_authorization):
                if authorization:
                    self.domains.delete_dns_authorization(name=authorization)

            self.domain_repository.delete(domain=domain)

            logger.info(
                "Custom domain removed",
                extra={"event": "domain_removed", "result": "success", "reason": f"domain={domain.id}"},
            )

    # ------------------------------------------------------------------
    # The load balancer
    # ------------------------------------------------------------------

    @transactional
    def _apply_routing(self) -> bool:
        """
        Serve every business's current certificates and redirects, then
        delete retired certificates. Returns whether anything changed.
        """
        self._begin()

        serving = self.domain_repository.certificates_in_state(state="active")

        self.domains.apply_routing(
            certificates=[certificate.name for certificate in serving],
            redirects=self._redirects(),
        )

        now = self.domain_repository.now()
        changed = False

        for certificate in serving:
            if certificate.attached_at is None:
                self.domain_repository.update_certificate(certificate=certificate, values={"attached_at": now})
                changed = True

        for certificate in self.domain_repository.certificates_in_state(state="retiring"):
            self.domains.delete_certificate(name=certificate.name)
            self.domain_repository.delete_certificate(certificate=certificate)
            changed = True

        return changed

    def _redirects(self) -> list[SiteRedirect]:
        """
        For each business with a live main domain: its generated host, the
        main domain's www and its live redirect domains (and theirs) go to
        the main domain.
        """
        redirects = []

        for tenant, live in self.domain_repository.live_sites():
            hosts = {f"{tenant.code}.{settings.BASE_DOMAIN}".lower()}

            for domain in live:
                hosts.update(domain_hostnames(domain))

            hosts.discard(tenant.custom_domain)

            redirects.append(SiteRedirect(key=tenant.code, hosts=tuple(sorted(hosts)), target=tenant.custom_domain))

        return redirects
