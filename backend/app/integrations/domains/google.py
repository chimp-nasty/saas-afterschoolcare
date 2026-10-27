import logging
import uuid

import dns.exception
import dns.resolver
from google.api_core.exceptions import NotFound
from google.cloud import certificate_manager_v1 as certificate_manager
from google.cloud import compute_v1 as compute

from app.core.config import settings
from app.integrations.domains.base import CertificateStatus, CloudResource, DnsAuthorization, DomainProvider, SiteRedirect


logger = logging.getLogger("app.domains")

# Long-running operations (creating and deleting) normally finish in seconds.
OPERATION_TIMEOUT_SECONDS = 120

# The load balancer's own routes (deploy/gcp/url-map.yaml) are left alone;
# businesses' redirects are the path matchers named with this prefix.
REDIRECT_PREFIX = "site-"

# Public resolvers: what the rest of the world sees, not a cached answer
# near us.
PUBLIC_RESOLVERS = ["8.8.8.8", "1.1.1.1"]
DNS_TIMEOUT_SECONDS = 5


def _bare(name: str) -> str:
    return name.lower().rstrip(".")


class GoogleDomains(DomainProvider):
    """
    Deployed (DOMAINS_PROVIDER=google): Certificate Manager for
    certificates, the regional load balancer (deploy/gcp/README.md) for
    serving them and for redirects, public DNS for the owner's records.
    Credentials are the API's service account (Application Default
    Credentials).
    """

    name = "google"

    def __init__(self):
        if not settings.GCP_PROJECT_ID:
            raise RuntimeError("GCP_PROJECT_ID is required for DOMAINS_PROVIDER=google")

        self._project = settings.GCP_PROJECT_ID
        self._region = settings.GCP_REGION
        self._parent = f"projects/{self._project}/locations/{self._region}"

        self._certificates = certificate_manager.CertificateManagerClient()
        self._proxies = compute.RegionTargetHttpsProxiesClient()
        self._url_maps = compute.RegionUrlMapsClient()

        self._resolver = dns.resolver.Resolver(configure=False)
        self._resolver.nameservers = PUBLIC_RESOLVERS
        self._resolver.lifetime = DNS_TIMEOUT_SECONDS

    # ------------------------------------------------------------------
    # Certificates
    # ------------------------------------------------------------------

    def create_dns_authorization(self, *, domain):
        operation = self._certificates.create_dns_authorization(
            parent=self._parent,
            dns_authorization_id=f"auth-{uuid.uuid4().hex[:24]}",
            dns_authorization=certificate_manager.DnsAuthorization(
                domain=domain,
                type_=certificate_manager.DnsAuthorization.Type.PER_PROJECT_RECORD,
            ),
        )
        authorization = operation.result(timeout=OPERATION_TIMEOUT_SECONDS)

        return DnsAuthorization(
            name=authorization.name,
            record_name=authorization.dns_resource_record.name,
            record_value=authorization.dns_resource_record.data,
        )

    def delete_dns_authorization(self, *, name):
        try:
            self._certificates.delete_dns_authorization(name=name).result(timeout=OPERATION_TIMEOUT_SECONDS)
        except NotFound:
            pass

    def create_certificate(self, *, name, hostnames, dns_authorizations):
        operation = self._certificates.create_certificate(
            parent=self._parent,
            certificate_id=name,
            certificate=certificate_manager.Certificate(
                managed=certificate_manager.Certificate.ManagedCertificate(
                    domains=hostnames,
                    dns_authorizations=dns_authorizations,
                ),
            ),
        )
        operation.result(timeout=OPERATION_TIMEOUT_SECONDS)

    def certificate_status(self, *, name):
        managed = self._certificates.get_certificate(name=self._certificate_path(name)).managed
        state = certificate_manager.Certificate.ManagedCertificate.State

        if managed.state == state.ACTIVE:
            return CertificateStatus(state="active")

        if managed.state == state.FAILED:
            reasons = [
                f"{attempt.domain}: {attempt.failure_reason.name}"
                for attempt in managed.authorization_attempt_info
                if attempt.failure_reason
            ]

            if managed.provisioning_issue and managed.provisioning_issue.reason:
                reasons.insert(0, managed.provisioning_issue.reason.name)

            return CertificateStatus(state="failed", reason="; ".join(reasons) or "The certificate couldn't be issued")

        return CertificateStatus(state="issuing")

    def delete_certificate(self, *, name):
        try:
            self._certificates.delete_certificate(name=self._certificate_path(name)).result(
                timeout=OPERATION_TIMEOUT_SECONDS
            )
        except NotFound:
            pass

    def list_certificates(self):
        return [
            CloudResource(name=certificate.name.rsplit("/", 1)[-1], created_at=certificate.create_time)
            for certificate in self._certificates.list_certificates(parent=self._parent)
        ]

    def list_dns_authorizations(self):
        return [
            CloudResource(name=authorization.name, created_at=authorization.create_time)
            for authorization in self._certificates.list_dns_authorizations(parent=self._parent)
        ]

    def _certificate_path(self, name: str) -> str:
        return f"{self._parent}/certificates/{name}"

    def _certificate_url(self, name: str) -> str:
        # The form gcloud sends for --certificate-manager-certificates (the
        # proxy refuses others with "Must be a valid ... Certificate Manager
        # certificate URL").
        return f"https://certificatemanager.googleapis.com/v1/{self._certificate_path(name)}"

    # ------------------------------------------------------------------
    # The load balancer
    # ------------------------------------------------------------------

    def apply_routing(self, *, certificates, redirects):
        self._apply_certificates(certificates)
        self._apply_redirects(redirects)

    def _apply_certificates(self, names: list[str]) -> None:
        wanted = [self._certificate_url(settings.LB_BASE_CERTIFICATE)] + [
            self._certificate_url(name) for name in sorted(names)
        ]

        proxy = self._proxies.get(project=self._project, region=self._region, target_https_proxy=settings.LB_HTTPS_PROXY)

        # Compared by name: the proxy may hand the URLs back in another form.
        if sorted(url.rsplit("/", 1)[-1] for url in proxy.ssl_certificates) == sorted(
            url.rsplit("/", 1)[-1] for url in wanted
        ):
            return

        self._proxies.set_ssl_certificates(
            project=self._project,
            region=self._region,
            target_https_proxy=settings.LB_HTTPS_PROXY,
            region_target_https_proxies_set_ssl_certificates_request_resource=compute.RegionTargetHttpsProxiesSetSslCertificatesRequest(
                ssl_certificates=wanted,
            ),
        ).result(timeout=OPERATION_TIMEOUT_SECONDS)

        logger.info(
            "Load balancer certificates changed",
            extra={"event": "domain_certificates_applied", "result": "success", "reason": f"certificates={len(wanted)}"},
        )

    def _apply_redirects(self, redirects: list[SiteRedirect]) -> None:
        url_map = self._url_maps.get(project=self._project, region=self._region, url_map=settings.LB_URL_MAP)

        api = (
            f"https://www.googleapis.com/compute/v1/projects/{self._project}"
            f"/regions/{self._region}/backendServices/{settings.LB_API_BACKEND}"
        )

        wanted_rules = [
            compute.HostRule(hosts=sorted(redirect.hosts), path_matcher=f"{REDIRECT_PREFIX}{redirect.key}")
            for redirect in sorted(redirects, key=lambda r: r.key)
        ]
        wanted_matchers = [
            compute.PathMatcher(
                name=f"{REDIRECT_PREFIX}{redirect.key}",
                default_url_redirect=compute.HttpRedirectAction(
                    host_redirect=redirect.target,
                    https_redirect=True,
                    redirect_response_code="MOVED_PERMANENTLY_DEFAULT",
                    strip_query=False,
                ),
                route_rules=[
                    compute.HttpRouteRule(
                        priority=1,
                        match_rules=[compute.HttpRouteRuleMatch(prefix_match="/api/")],
                        service=api,
                    )
                ],
            )
            for redirect in sorted(redirects, key=lambda r: r.key)
        ]

        kept_rules = [rule for rule in url_map.host_rules if not rule.path_matcher.startswith(REDIRECT_PREFIX)]
        kept_matchers = [matcher for matcher in url_map.path_matchers if not matcher.name.startswith(REDIRECT_PREFIX)]

        current_rules = [rule for rule in url_map.host_rules if rule.path_matcher.startswith(REDIRECT_PREFIX)]
        current_matchers = [matcher for matcher in url_map.path_matchers if matcher.name.startswith(REDIRECT_PREFIX)]

        if _same(current_rules, wanted_rules) and _same(current_matchers, wanted_matchers):
            return

        patch = compute.UrlMap(
            fingerprint=url_map.fingerprint,
            host_rules=kept_rules + wanted_rules,
            path_matchers=kept_matchers + wanted_matchers,
        )

        self._url_maps.patch(
            project=self._project,
            region=self._region,
            url_map=settings.LB_URL_MAP,
            url_map_resource=patch,
        ).result(timeout=OPERATION_TIMEOUT_SECONDS)

        logger.info(
            "Load balancer redirects changed",
            extra={"event": "domain_redirects_applied", "result": "success", "reason": f"businesses={len(redirects)}"},
        )

    # ------------------------------------------------------------------
    # Public DNS
    # ------------------------------------------------------------------

    def _answers(self, name: str, record_type: str) -> list:
        try:
            return list(self._resolver.resolve(name, record_type))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
            return []

    def has_txt(self, *, name, value):
        return any(
            b"".join(answer.strings).decode(errors="replace") == value
            for answer in self._answers(name, "TXT")
        )

    def has_cname(self, *, name, target):
        return any(_bare(answer.target.to_text()) == _bare(target) for answer in self._answers(name, "CNAME"))

    def points_to(self, *, name, address):
        addresses = {answer.address for answer in self._answers(name, "A")}

        # An IPv6 address elsewhere would send some visitors there instead.
        return addresses == {address} and not self._answers(name, "AAAA")


def _same(current: list, wanted: list) -> bool:
    """
    Compare the parts of the URL map we manage, ignoring their order. If
    Google reports a field differently from how we set it, the cost is an
    unneeded (identical) update.
    """

    def normalised(items):
        return sorted(str(type(item).to_dict(item)) for item in items)

    return normalised(current) == normalised(wanted)
