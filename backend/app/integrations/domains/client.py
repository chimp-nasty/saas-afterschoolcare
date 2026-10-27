from functools import cache

from app.core.config import settings
from app.integrations.domains.base import CertificateStatus, CloudResource, DnsAuthorization, DomainProvider, SiteRedirect


@cache
def _provider(name: str) -> DomainProvider:
    # Imported here so Google's SDKs are only loaded (and credentials looked
    # up) when they're used, once per process.
    if name == "google":
        from app.integrations.domains.google import GoogleDomains

        return GoogleDomains()

    from app.integrations.domains.local import LocalDomains

    return LocalDomains()


class DomainsClient:
    """
    Custom domains' certificates, the load balancer's routing and public DNS
    (docs/tenant-administration.md, section 7). The provider comes from
    DOMAINS_PROVIDER: "local" in development, "google" when deployed.
    """

    def __init__(self):
        self._provider = _provider(settings.DOMAINS_PROVIDER)

    def create_dns_authorization(self, *, domain: str) -> DnsAuthorization:
        return self._provider.create_dns_authorization(domain=domain)

    def delete_dns_authorization(self, *, name: str) -> None:
        self._provider.delete_dns_authorization(name=name)

    def create_certificate(self, *, name: str, hostnames: list[str], dns_authorizations: list[str]) -> None:
        self._provider.create_certificate(name=name, hostnames=hostnames, dns_authorizations=dns_authorizations)

    def certificate_status(self, *, name: str) -> CertificateStatus:
        return self._provider.certificate_status(name=name)

    def delete_certificate(self, *, name: str) -> None:
        self._provider.delete_certificate(name=name)

    def list_certificates(self) -> list[CloudResource]:
        return self._provider.list_certificates()

    def list_dns_authorizations(self) -> list[CloudResource]:
        return self._provider.list_dns_authorizations()

    def apply_routing(self, *, certificates: list[str], redirects: list[SiteRedirect]) -> None:
        self._provider.apply_routing(certificates=certificates, redirects=redirects)

    def has_txt(self, *, name: str, value: str) -> bool:
        return self._provider.has_txt(name=name, value=value)

    def has_cname(self, *, name: str, target: str) -> bool:
        return self._provider.has_cname(name=name, target=target)

    def points_to(self, *, name: str, address: str) -> bool:
        return self._provider.points_to(name=name, address=address)
