from urllib.parse import urlencode

from app.core.config import settings


def tenant_site(*, tenant_code: str, custom_domain: str | None) -> str:
    """
    The tenant's site: its custom domain if it has one, else
    FRONTEND_URL_TEMPLATE (dev), else https://{tenant}.<BASE_DOMAIN>.
    """
    if custom_domain:
        base = f"https://{custom_domain}"
    elif settings.FRONTEND_URL_TEMPLATE:
        base = settings.FRONTEND_URL_TEMPLATE.format(tenant=tenant_code)
    else:
        base = f"https://{tenant_code}.{settings.BASE_DOMAIN}"

    return base.rstrip("/")


class Links:
    """Links into the tenant's site for one location (tenant_site)."""

    def __init__(self, *, tenant_code: str, custom_domain: str | None, location_code: str):
        self._root = f"{tenant_site(tenant_code=tenant_code, custom_domain=custom_domain)}/{location_code}"

    def url(self, path: str = "", **query: str) -> str:
        url = f"{self._root}/{path.lstrip('/')}" if path else self._root

        return f"{url}?{urlencode(query)}" if query else url
