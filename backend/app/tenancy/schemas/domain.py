import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


# Business settings › Domains (docs/tenant-administration.md, section 7).

# As ck_tenant_domains_hostname: letters, digits and hyphens, at least two
# labels, the last starting with a letter.
_HOSTNAME = re.compile(r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$")

DomainState = Literal["pending_dns", "verified", "active", "suspended", "failed", "removing"]


def normalise_hostname(value: str) -> str:
    """
    What the owner typed (perhaps a whole address, in capitals, or an
    international name) as a bare hostname: lower case, punycode, no
    scheme, path or trailing dot.
    """
    hostname = value.strip().lower()
    hostname = re.sub(r"^[a-z]+://", "", hostname)
    hostname = re.split(r"[/?#:]", hostname, maxsplit=1)[0].rstrip(".")

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Enter a domain like after3.com.au") from exc

    if len(hostname) > 253 or not _HOSTNAME.match(hostname):
        raise ValueError("Enter a domain like after3.com.au")

    return hostname


class AddDomainRequest(BaseModel):
    hostname: str
    # The business's main domain (where its site moves to), or one sending
    # visitors to it.
    is_main: bool
    # www.<hostname> too (ignored for a hostname that starts with www.).
    include_www: bool = True

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, value: str) -> str:
        return normalise_hostname(value)


class DnsRecordResponse(BaseModel):
    type: Literal["TXT", "CNAME", "A"]
    name: str
    value: str
    # Found by the last check.
    seen: bool
    # What the record is for, shown beside it.
    purpose: str


class DomainResponse(BaseModel):
    id: UUID
    hostname: str
    is_main: bool
    include_www: bool
    state: DomainState
    failure_reason: str | None
    # The records the owner adds at their DNS host.
    records: list[DnsRecordResponse]
    created_at: datetime
    last_checked_at: datetime | None
    active_at: datetime | None


class DomainsResponse(BaseModel):
    # Custom domains are set up here (the load balancer's address is known).
    available: bool
    # The business's own address on the platform, always working.
    generated_host: str
    # The live main domain: where the business's site is.
    live_domain: str | None
    domains: list[DomainResponse]


class DomainCheckResponse(BaseModel):
    businesses_checked: int
