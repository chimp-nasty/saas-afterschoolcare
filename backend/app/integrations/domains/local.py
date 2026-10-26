import logging
import uuid

from app.integrations.domains.base import CertificateStatus, DnsAuthorization, DomainProvider, SiteRedirect


logger = logging.getLogger("app.domains")


class LocalDomains(DomainProvider):
    """
    Development (DOMAINS_PROVIDER=local): there's no load balancer or public
    DNS to ask, so every record is found and every certificate is issued at
    once. A domain goes live on its first check, which shows the whole flow
    in Business settings; browsing it needs a real deployment.
    """

    name = "local"

    def create_dns_authorization(self, *, domain):
        suffix = uuid.uuid4().hex[:6]

        return DnsAuthorization(
            name=f"local-auth-{suffix}",
            record_name=f"_acme-challenge_{suffix}.{domain}.",
            record_value=f"{suffix}.local.authorize.certificatemanager.goog.",
        )

    def delete_dns_authorization(self, *, name):
        return None

    def create_certificate(self, *, name, hostnames, dns_authorizations):
        return None

    def certificate_status(self, *, name):
        return CertificateStatus(state="active")

    def delete_certificate(self, *, name):
        return None

    def apply_routing(self, *, certificates, redirects: list[SiteRedirect]):
        logger.info(
            "Routing applied (local: nothing to change)",
            extra={
                "event": "domain_routing_applied",
                "result": "success",
                "reason": f"certificates={len(certificates)}; redirects={len(redirects)}",
            },
        )

    def has_txt(self, *, name, value):
        return True

    def has_cname(self, *, name, target):
        return True

    def points_to(self, *, name, address):
        return True
