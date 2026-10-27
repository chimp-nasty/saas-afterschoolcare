import hmac

from fastapi import APIRouter, Depends, Header

from app.api.response import ApiResponse
from app.core.config import settings
from app.dependencies.db import get_db
from app.dependencies.platform import require_platform_site
from app.dependencies.service import get_service
from app.errors.payments import PaymentCheckDeniedError
from app.public.schemas.payment_check import PaymentCheckResponse
from app.public.services.payment_check import PaymentCheckService


# The scheduled payment check (docs/payment-confirmation.md): Cloud
# Scheduler calls it every 5 minutes on the platform's own site, with
# PAYMENT_CHECK_SECRET in X-Payment-Check-Secret (deploy/gcp/README.md). No
# user and no permission: the secret is the authority, and the service acts
# as server code (the payment_check RLS channel).
router = APIRouter(
    prefix="/internal/v1",
    tags=["internal"],
)

_service = get_service(PaymentCheckService, db_dependency=get_db)


def require_payment_check_secret(
    x_payment_check_secret: str | None = Header(default=None),
    _: None = Depends(require_platform_site),
) -> None:
    expected = settings.PAYMENT_CHECK_SECRET

    if not expected or not x_payment_check_secret or not hmac.compare_digest(x_payment_check_secret, expected):
        raise PaymentCheckDeniedError()


@router.post("/payment-check")
def run_payment_check(
    _: None = Depends(require_payment_check_secret),
    service: PaymentCheckService = Depends(_service),
) -> ApiResponse[PaymentCheckResponse]:
    return ApiResponse(
        ok=True,
        msg="Payments checked",
        data=PaymentCheckResponse(payments_checked=service.check_all()),
    )
