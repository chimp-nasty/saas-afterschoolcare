from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import RedirectResponse

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.db import get_db
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.errors.payments import StripeOAuthStateError
from app.tenancy.schemas.stripe_account import StripeAccountStatusResponse, StripeOnboardingResponse
from app.tenancy.services.stripe_connect import StripeConnectService


# Admin › Payments (slice 5): the business's Stripe account (Stripe
# Connect). stripe_account r: admins and superadmins see whether it can
# take payments; stripe_account u: superadmins connect it (Stripe's hosted
# onboarding, or "Connect with Stripe" to link an existing account),
# refresh its status and turn payments off or on. A business setting, so
# superadmins only, like service settings.
router = APIRouter(
    prefix="/stripe-account/v1",
    tags=["stripe-account"],
)

_service = get_service(StripeConnectService, db_dependency=get_rls_db)


@router.get("/")
def get_stripe_account(
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="r")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(ok=True, msg="Fetched payments account", data=service.status(location_id=ctx.location_id))


# A one-time link to Stripe's onboarding, which returns to Admin › Payments
# on this location's site (checked against the request's Origin).
@router.post("/onboarding")
def start_stripe_onboarding(
    origin: str | None = Header(default=None),
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeOnboardingResponse]:
    return ApiResponse(
        ok=True,
        msg="Continuing to Stripe",
        data=service.onboarding_link(location_id=ctx.location_id, origin=origin),
    )


# "Connect with Stripe": a link to Stripe's page for linking the business's
# existing account (OAuth). Stripe returns to the callback below.
@router.post("/oauth")
def start_stripe_oauth(
    origin: str | None = Header(default=None),
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeOnboardingResponse]:
    return ApiResponse(
        ok=True,
        msg="Continuing to Stripe",
        data=service.oauth_link(location_id=ctx.location_id, user_id=ctx.user_id, origin=origin),
    )


# Stripe's OAuth returns the browser here (one registered address for every
# tenant). No login is needed: the signed state says who started it, and
# the account is saved as them (RLS: a superadmin of that business). Sends
# them back to Admin › Payments on their own site.
@router.get("/oauth/callback")
def finish_stripe_oauth(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: StripeConnectService = Depends(get_service(StripeConnectService, db_dependency=get_db)),
):
    url = service.complete_oauth(code=code, state=state, error=error)

    if not url:
        raise StripeOAuthStateError(log_reason="Stripe OAuth callback with an unknown or expired state")

    return RedirectResponse(url, status_code=303)


@router.post("/refresh")
def refresh_stripe_account(
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(ok=True, msg="Payments account refreshed", data=service.refresh(location_id=ctx.location_id))


@router.post("/disconnect")
def disconnect_stripe_account(
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(
        ok=True,
        msg="Online payments turned off",
        data=service.set_disconnected(location_id=ctx.location_id, disconnected=True),
    )


@router.post("/reconnect")
def reconnect_stripe_account(
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(
        ok=True,
        msg="Online payments turned on",
        data=service.set_disconnected(location_id=ctx.location_id, disconnected=False),
    )
