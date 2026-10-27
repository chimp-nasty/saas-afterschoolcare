from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class DnsAuthorization:
    """
    Certificate Manager's proof that a domain points at our project: a
    CNAME record the owner adds, kept for renewals.
    """

    name: str
    record_name: str
    record_value: str


@dataclass(frozen=True)
class CertificateStatus:
    state: Literal["issuing", "active", "failed"]
    reason: str | None = None


@dataclass(frozen=True)
class CloudResource:
    """
    A certificate or DNS authorization that exists in Certificate Manager,
    named as the app stores it (a certificate's id; an authorization's
    full name), for finding ones the database no longer knows.
    """

    name: str
    created_at: datetime


@dataclass(frozen=True)
class SiteRedirect:
    """
    One business's load balancer rule: page loads on `hosts` get a
    permanent redirect to `target` (its main domain), keeping the path.
    /api on them still reaches the API.
    """

    key: str
    hosts: tuple[str, ...]
    target: str


class DomainProvider(ABC):
    """
    What custom domains need from the cloud and from DNS
    (docs/tenant-administration.md, section 7). One implementation per
    setting of DOMAINS_PROVIDER; DomainsClient picks it, and services only
    ever see DomainsClient.
    """

    name: str

    # -- Certificates (Certificate Manager) --

    @abstractmethod
    def create_dns_authorization(self, *, domain: str) -> DnsAuthorization: ...

    @abstractmethod
    def delete_dns_authorization(self, *, name: str) -> None:
        """Gone already counts as deleted."""

    @abstractmethod
    def create_certificate(self, *, name: str, hostnames: list[str], dns_authorizations: list[str]) -> None: ...

    @abstractmethod
    def certificate_status(self, *, name: str) -> CertificateStatus: ...

    @abstractmethod
    def delete_certificate(self, *, name: str) -> None:
        """Gone already counts as deleted."""

    @abstractmethod
    def list_certificates(self) -> list[CloudResource]:
        """Every certificate in the project's region, the platform's own included."""

    @abstractmethod
    def list_dns_authorizations(self) -> list[CloudResource]:
        """Every DNS authorization in the project's region, the platform's own included."""

    # -- The load balancer --

    @abstractmethod
    def apply_routing(self, *, certificates: list[str], redirects: list[SiteRedirect]) -> None:
        """
        Make the load balancer serve exactly these businesses' certificates
        (beside the platform's own) and these redirects. Called with the
        whole set every time; nothing changes when it already matches.
        """

    # -- Public DNS --

    @abstractmethod
    def has_txt(self, *, name: str, value: str) -> bool: ...

    @abstractmethod
    def has_cname(self, *, name: str, target: str) -> bool: ...

    @abstractmethod
    def points_to(self, *, name: str, address: str) -> bool:
        """The name resolves to the address (directly or through CNAMEs), and only to it."""
