from urllib.parse import urlparse

from app.core.config import settings
from app.db.models import Location, Tenant
from app.errors.bookings import CheckoutOriginError


def location_site_url(
    *,
    location: Location,
    tenant: Tenant,
    origin: str | None,
) -> str:
    """
    The location's frontend URL, for Stripe's return links (checkout and
    onboarding). Built from the request's Origin (so dev ports work) but
    only once it's checked to be this tenant's site, so it can't be used as
    an open redirect.
    """
    hostname = (urlparse(origin).hostname or "").lower() if origin else ""

    allowed_hostnames = {
        f"{tenant.code}.{settings.BASE_DOMAIN}".lower(),
    }

    if tenant.custom_domain:
        allowed_hostnames.add(tenant.custom_domain.lower())

    if hostname not in allowed_hostnames:
        raise CheckoutOriginError()

    return f"{origin.rstrip('/')}/{location.code}"
