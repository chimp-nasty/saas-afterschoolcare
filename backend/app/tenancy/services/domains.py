import logging
import secrets
from uuid import UUID

from google.api_core.exceptions import GoogleAPIError
from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.core.config import settings
from app.db.models import TenantDomain
from app.db.transaction import transactional
from app.errors.tenancy import (
    DomainNotFoundError,
    DomainPlatformError,
    DomainProviderError,
    DomainsNotAvailableError,
)
from app.integrations.domains.base import DnsAuthorization
from app.integrations.domains.client import DomainsClient
from app.tenancy.repositories.tenant import TenantRepository
from app.tenancy.repositories.tenant_domain import TenantDomainRepository
from app.tenancy.schemas.domain import AddDomainRequest, DnsRecordResponse, DomainResponse, DomainsResponse
from app.tenancy.services.domain_check import DomainCheckService, verify_record_name


logger = logging.getLogger("app.domains")


def _bare(name: str) -> str:
    return name.rstrip(".")


def _records(domain: TenantDomain) -> list[DnsRecordResponse]:
    """The records the owner adds at their DNS host, as the check looks for them."""
    address = settings.DOMAINS_TARGET_IP or ""

    records = [
        DnsRecordResponse(
            type="TXT",
            name=verify_record_name(domain.hostname),
            value=domain.verification_token,
            seen=domain.txt_seen,
            purpose="Proves the domain is yours",
        ),
        DnsRecordResponse(
            type="CNAME",
            name=_bare(domain.auth_record_name),
            value=_bare(domain.auth_record_value),
            seen=domain.auth_seen,
            purpose="Lets Google issue its certificate (keep it: renewals use it)",
        ),
        DnsRecordResponse(
            type="A",
            name=domain.hostname,
            value=address,
            seen=domain.address_seen,
            purpose="Points the domain at your site",
        ),
    ]

    if domain.include_www:
        records += [
            DnsRecordResponse(
                type="CNAME",
                name=_bare(domain.www_auth_record_name),
                value=_bare(domain.www_auth_record_value),
                seen=domain.www_auth_seen,
                purpose="Lets Google issue the certificate for www",
            ),
            DnsRecordResponse(
                type="A",
                name=f"www.{domain.hostname}",
                value=address,
                seen=domain.www_address_seen,
                purpose="Points www at your site",
            ),
        ]

    return records


def _to_response(domain: TenantDomain) -> DomainResponse:
    return DomainResponse(
        id=domain.id,
        hostname=domain.hostname,
        is_main=domain.is_main,
        include_www=domain.include_www,
        state=domain.state,
        failure_reason=domain.failure_reason,
        records=_records(domain),
        created_at=domain.created_at,
        last_checked_at=domain.last_checked_at,
        active_at=domain.active_at,
    )


class DomainService:
    """
    Business settings › Domains (docs/tenant-administration.md, section 7):
    the owner adds the business's main domain and up to 4 domains sending
    visitors to it, sees the DNS records each needs and how far it's got,
    and removes them. RLS checks tenant_domains on every read and write; the
    database's rules (schema/0002) keep everything else to the domain check
    (DomainCheckService), which this runs for the business after a removal
    and on "Check now".
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
        self.check = DomainCheckService(
            db=db,
            rls_context=rls_context,
            domain_repository=domain_repository,
            tenant_repository=tenant_repository,
        )

    def list_domains(
        self,
        *,
        tenant_id: UUID,
    ) -> DomainsResponse:
        tenant = self.tenant_repository.get_by_id(id=tenant_id)

        return DomainsResponse(
            available=bool(settings.DOMAINS_TARGET_IP),
            generated_host=f"{tenant.code}.{settings.BASE_DOMAIN}",
            live_domain=tenant.custom_domain,
            domains=[_to_response(domain) for domain in self.domain_repository.list_for_tenant(tenant_id=tenant_id)],
        )

    def add_domain(
        self,
        *,
        tenant_id: UUID,
        body: AddDomainRequest,
    ) -> DomainResponse:
        if not settings.DOMAINS_TARGET_IP:
            raise DomainsNotAvailableError()

        base_domain = settings.BASE_DOMAIN.lower()

        if body.hostname == base_domain or body.hostname.endswith(f".{base_domain}"):
            raise DomainPlatformError()

        include_www = body.include_www and not body.hostname.startswith("www.")

        # Google's authorizations first: the database only records what
        # exists. If saving then fails (the domain was already added), they
        # are deleted again.
        authorizations = self._authorize(hostname=body.hostname, include_www=include_www)

        try:
            return self._save(tenant_id=tenant_id, body=body, include_www=include_www, authorizations=authorizations)
        except Exception:
            for authorization in authorizations:
                self._delete_authorization(name=authorization.name)

            raise

    def _authorize(
        self,
        *,
        hostname: str,
        include_www: bool,
    ) -> list[DnsAuthorization]:
        created: list[DnsAuthorization] = []

        try:
            for name in [hostname, f"www.{hostname}"] if include_www else [hostname]:
                created.append(self.domains.create_dns_authorization(domain=name))
        except GoogleAPIError as exc:
            for authorization in created:
                self._delete_authorization(name=authorization.name)

            raise DomainProviderError(log_reason=str(exc)) from exc

        return created

    def _delete_authorization(self, *, name: str) -> None:
        try:
            self.domains.delete_dns_authorization(name=name)
        except GoogleAPIError:
            logger.exception(
                "Couldn't delete an unused DNS authorization",
                extra={"event": "domain_authorization_orphaned", "result": "failed", "reason": name},
            )

    @transactional
    def _save(
        self,
        *,
        tenant_id: UUID,
        body: AddDomainRequest,
        include_www: bool,
        authorizations: list[DnsAuthorization],
    ) -> DomainResponse:
        main = authorizations[0]
        www = authorizations[1] if include_www else None

        domain = self.domain_repository.add(
            values={
                "tenant_id": tenant_id,
                "hostname": body.hostname,
                "is_main": body.is_main,
                "include_www": include_www,
                "verification_token": secrets.token_urlsafe(24),
                "dns_authorization": main.name,
                "auth_record_name": main.record_name,
                "auth_record_value": main.record_value,
                "www_dns_authorization": www.name if www else None,
                "www_auth_record_name": www.record_name if www else None,
                "www_auth_record_value": www.record_value if www else None,
            },
        )

        logger.info(
            "Custom domain added",
            extra={"event": "domain_added", "result": "success", "reason": f"domain={domain.id}; main={body.is_main}"},
        )

        return _to_response(domain)

    def remove_domain(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        domain_id: UUID,
    ) -> DomainsResponse:
        """
        It stops working at once: the check runs for the business now, so
        its site goes back to the generated host and the load balancer stops
        sending the domain anywhere. Google's certificate and authorizations
        go as the check gets to them.
        """
        self._mark_removing(tenant_id=tenant_id, domain_id=domain_id)
        self._run_check(tenant_id=tenant_id, user_id=user_id)

        return self.list_domains(tenant_id=tenant_id)

    @transactional
    def _mark_removing(
        self,
        *,
        tenant_id: UUID,
        domain_id: UUID,
    ) -> None:
        domain = self.domain_repository.get(tenant_id=tenant_id, id=domain_id)

        if domain is None:
            raise DomainNotFoundError()

        if domain.state != "removing":
            self.domain_repository.update(domain=domain, values={"state": "removing"})

    def check_now(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
    ) -> DomainsResponse:
        self._run_check(tenant_id=tenant_id, user_id=user_id)

        return self.list_domains(tenant_id=tenant_id)

    def _run_check(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        The domain check for this business, in its own transactions with no
        user (the owner's permission was checked by the route): the owner's
        transaction ends first, since the check's channel only counts
        without a user. Afterwards the owner's RLS setting is put back for
        the reads that follow.
        """
        self.db.commit()

        try:
            self.check.check_tenant(tenant_id=tenant_id)
        except GoogleAPIError as exc:
            raise DomainProviderError(log_reason=str(exc)) from exc
        finally:
            self.rls_context.set_user_id(user_id=user_id)
