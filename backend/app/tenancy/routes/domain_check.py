import hmac

from fastapi import APIRouter, Depends, Header

from app.api.response import ApiResponse
from app.core.config import settings
from app.dependencies.db import get_db
from app.dependencies.platform import require_platform_site
from app.dependencies.service import get_service
from app.errors.tenancy import DomainCheckDeniedError
from app.tenancy.schemas.domain import DomainCheckResponse
from app.tenancy.services.domain_check import DomainCheckService


# The scheduled domain check (docs/tenant-administration.md, section 7):
# Cloud Scheduler calls it every 5 minutes on the platform's own site, with
# DOMAINS_CHECK_SECRET in X-Domain-Check-Secret (deploy/gcp/README.md). No
# user and no permission: the secret is the authority, and the service acts
# as server code (the domain_check RLS channel).
router = APIRouter(
    prefix="/internal/v1",
    tags=["internal"],
)

_service = get_service(DomainCheckService, db_dependency=get_db)


def require_check_secret(
    x_domain_check_secret: str | None = Header(default=None),
    _: None = Depends(require_platform_site),
) -> None:
    expected = settings.DOMAINS_CHECK_SECRET

    if not expected or not x_domain_check_secret or not hmac.compare_digest(x_domain_check_secret, expected):
        raise DomainCheckDeniedError()


@router.post("/domain-check")
def run_domain_check(
    _: None = Depends(require_check_secret),
    service: DomainCheckService = Depends(_service),
) -> ApiResponse[DomainCheckResponse]:
    return ApiResponse(
        ok=True,
        msg="Domains checked",
        data=DomainCheckResponse(businesses_checked=service.check_all()),
    )
