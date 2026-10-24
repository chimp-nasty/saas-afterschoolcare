from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission, require_tenant_permission, site_origin
from app.dependencies.db import get_db
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.errors.payments import StripeOAuthStateError
from app.tenancy.schemas.stripe_account import StripeAccountStatusResponse, StripeOnboardingResponse
from app.tenancy.services.stripe_connect import StripeConnectService


# The business's Stripe account (Stripe Connect; slice 5). Managed in
# Business settings › Payments (/business/payments) by the tenant's owner
# (tenant_stripe_account r/u: connect it through Stripe's hosted onboarding
# or "Connect with Stripe", refresh its status, turn payments off or on).
# A centre's admins and superadmins only see whether it takes payments
# (stripe_account r, Admin › Payments). docs/tenant-administration.md.
router = APIRouter(
    prefix="/stripe-account/v1",
    tags=["stripe-account"],
)

_service = get_service(StripeConnectService, db_dependency=get_rls_db)


# A centre's admin pages: read only.
@router.get("/")
def get_stripe_account(
    ctx: TokenContext = Depends(require_permission(resource="stripe_account", action="r")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(ok=True, msg="Fetched payments account", data=service.status(tenant_id=ctx.tenant_id))


# Business settings: the same, for the owner (who may have no location).
@router.get("/tenant")
def get_tenant_stripe_account(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_stripe_account", action="r")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(ok=True, msg="Fetched payments account", data=service.status(tenant_id=ctx.tenant_id))


# A one-time link to Stripe's onboarding, which returns to Business
# settings › Payments on this tenant's site.
@router.post("/onboarding")
def start_stripe_onboarding(
    origin: str = Depends(site_origin),
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeOnboardingResponse]:
    return ApiResponse(
        ok=True,
        msg="Continuing to Stripe",
        data=service.onboarding_link(tenant_id=ctx.tenant_id, origin=origin),
    )


# "Connect with Stripe": a link to Stripe's page for linking the business's
# existing account (OAuth). Stripe returns to the callback below.
@router.post("/oauth")
def start_stripe_oauth(
    origin: str = Depends(site_origin),
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeOnboardingResponse]:
    return ApiResponse(
        ok=True,
        msg="Continuing to Stripe",
        data=service.oauth_link(tenant_id=ctx.tenant_id, user_id=ctx.user_id, origin=origin),
    )


# Stripe's OAuth returns the browser here (one registered address for every
# tenant). No login is needed: the signed state says who started it, and
# the account is saved as them (RLS: the owner of that business). Sends
# them back to Business settings › Payments on their own site.
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
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(ok=True, msg="Payments account refreshed", data=service.refresh(tenant_id=ctx.tenant_id))


@router.post("/disconnect")
def disconnect_stripe_account(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(
        ok=True,
        msg="Online payments turned off",
        data=service.set_disconnected(tenant_id=ctx.tenant_id, disconnected=True),
    )


@router.post("/reconnect")
def reconnect_stripe_account(
    ctx: TokenContext = Depends(require_tenant_permission(resource="tenant_stripe_account", action="u")),
    service: StripeConnectService = Depends(_service),
) -> ApiResponse[StripeAccountStatusResponse]:
    return ApiResponse(
        ok=True,
        msg="Online payments turned on",
        data=service.set_disconnected(tenant_id=ctx.tenant_id, disconnected=False),
    )
