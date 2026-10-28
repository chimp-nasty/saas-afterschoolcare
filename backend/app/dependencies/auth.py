from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import Cookie, Depends, Request

from app.core.config import settings
from app.dependencies.db import get_db
from app.auth.jwt.context import (
    TokenContext,
    build_token_context,
)
from app.auth.jwt.tokens import TokenService
from app.errors.auth import PermissionNotFoundError, JwtInvalidError
from app.errors.customer import AccountDeactivatedError
from app.public.repositories.family_deactivation import FamilyDeactivationRepository
from app.errors.tenancy import LocationNotFoundError
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.repositories.tenant import TenantRepository


def get_current_token_context(
    request: Request,
    access_token: str | None = Cookie(
        default=None,
    ),
    db: Session = Depends(get_db),
) -> TokenContext:
    if not access_token:
        raise JwtInvalidError()

    claims = TokenService.decode_access_token(
        access_token,
    )

    ctx = build_token_context(
        claims,
    )

    # A token only counts on its own tenant's site.
    tenant = _resolve_tenant(request=request, db=db)

    if ctx.tenant_id != tenant.id:
        raise JwtInvalidError()

    return ctx


def require_permission(
    *,
    resource: str,
    action: str,
    allow_deactivated: bool = False,
) -> Callable[..., TokenContext]:
    """
    The token's permission at its location. A family deactivated there
    (docs/account-deactivation.md) is refused everything, checked live on
    every request so it applies to logins already open, except the few
    endpoints that pass `allow_deactivated` (reading their own account and
    asking to be reactivated). RLS hides their rows as well.
    """
    def dependency(
        ctx: TokenContext = Depends(
            get_current_token_context,
        ),
        db: Session = Depends(get_db),
    ) -> TokenContext:
        actions = ctx.permissions.get(
            resource,
        )

        # A token without a location (Business settings) has no location
        # permissions; refused here too, so routes can rely on one.
        if (
            ctx.location_id is None
            or actions is None
            or action not in actions
        ):
            raise PermissionNotFoundError()

        # Only families can be deactivated (the database refuses anyone else).
        if (
            not allow_deactivated
            and "customer" in ctx.roles
            and FamilyDeactivationRepository(db=db).is_deactivated(user_id=ctx.user_id, location_id=ctx.location_id)
        ):
            raise AccountDeactivatedError()

        return ctx

    return dependency


def require_tenant_permission(
    *,
    resource: str,
    action: str,
) -> Callable[..., TokenContext]:
    """
    A permission across the whole tenant (docs/tenant-administration.md),
    held by its owner whichever location they're logged in at. Kept apart
    from require_permission: a location permission never satisfies it, nor
    the other way round. RLS checks the grant again, live.
    """
    def dependency(
        ctx: TokenContext = Depends(
            get_current_token_context,
        ),
    ) -> TokenContext:
        actions = ctx.tenant_permissions.get(
            resource,
        )

        if (
            actions is None
            or action not in actions
        ):
            raise PermissionNotFoundError()

        return ctx

    return dependency


def _resolve_tenant(
    *,
    request: Request,
    db: Session,
):
    """
    The tenant whose site the request is for: tenant1.<BASE_DOMAIN>, or a
    tenant's own custom domain. Read from the Host header, which the load
    balancer (and Vite's proxy in dev) passes through unchanged; the API is
    served on each tenant's own site, under /api.
    """
    hostname = request.url.hostname

    if not hostname:
        raise LocationNotFoundError()

    hostname = hostname.lower()

    tenants = TenantRepository(db=db)

    base_domain = settings.BASE_DOMAIN.lower()
    generated_domain_suffix = f".{base_domain}"

    if hostname.endswith(generated_domain_suffix):
        tenant_code = hostname.removesuffix(
            generated_domain_suffix,
        )

        tenant = tenants.get_by_code(
            code=tenant_code,
        )

    else:
        tenant = tenants.get_by_custom_domain(
            custom_domain=hostname,
        )

    # A tenant the platform has switched off answers as if it didn't exist.
    if not tenant or not tenant.is_active:
        raise LocationNotFoundError()

    return tenant


def site_origin(
    request: Request,
) -> str:
    """
    The site the request is for (scheme, host and port), for links back to
    it such as Stripe's return URLs. location_site_url checks it belongs to
    the tenant.
    """
    return f"{request.url.scheme}://{request.url.netloc}"


def resolve_tenant_id(
    request: Request,
    db: Session = Depends(get_db),
) -> UUID:
    return _resolve_tenant(request=request, db=db).id


def resolve_location_id(
    location_code: str,
    request: Request,
    db: Session = Depends(get_db),
) -> UUID:
    tenant = _resolve_tenant(request=request, db=db)

    location = LocationRepository(db=db).get_by_tenant_and_code(
        tenant_id=tenant.id,
        code=location_code,
    )

    if not location:
        raise LocationNotFoundError()

    return location.id
