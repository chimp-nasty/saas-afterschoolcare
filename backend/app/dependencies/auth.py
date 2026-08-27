from urllib.parse import urlparse
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import Cookie, Depends, Header

from app.core.config import settings
from app.dependencies.db import get_db
from app.auth.jwt.context import (
    TokenContext,
    build_token_context,
)
from app.auth.jwt.tokens import TokenService
from app.auth.scope import AuthorizationScope
from app.errors.auth import PermissionNotFoundError, JwtInvalidError
from app.errors.tenancy import LocationNotFoundError
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.repositories.tenant import TenantRepository


def get_current_token_context(
    access_token: str | None = Cookie(
        default=None,
    ),
) -> TokenContext:
    if not access_token:
        raise JwtInvalidError()

    claims = TokenService.decode_access_token(
        access_token,
    )

    return build_token_context(
        claims,
    )
    

def resolve_scope(
    *,
    ctx: TokenContext,
    resource: str,
    action: str,
    target_user_id: UUID | None = None,
) -> AuthorizationScope:
    required_scope = (
        "l"
        if target_user_id is not None
        else "s"
    )

    actions = ctx.permissions.get(
        resource,
    )

    if actions is None:
        raise PermissionNotFoundError()

    scopes = actions.get(
        action,
    )

    if (
        scopes is None
        or required_scope not in scopes
    ):
        raise PermissionNotFoundError()

    return AuthorizationScope(
        location_id=ctx.location_id,
        user_id=(
            target_user_id
            if target_user_id is not None
            else ctx.user_id
        ),
    )


def require_scope(
    *,
    resource: str,
    action: str,
) -> Callable[..., AuthorizationScope]:
    def dependency(
        user_id: UUID | None = None,
        ctx: TokenContext = Depends(
            get_current_token_context,
        ),
    ) -> AuthorizationScope:
        return resolve_scope(
            ctx=ctx,
            resource=resource,
            action=action,
            target_user_id=user_id,
        )

    return dependency


def resolve_location_id(
    location_code: str,
    origin: str | None = Header(
        default=None,
    ),
    db: Session = Depends(get_db),
) -> UUID:
    """
    Resolve public request context to a trusted location ID.

    Resolves the tenant from the frontend origin, then resolves
    the requested location code within that tenant.
    """
    if not origin:
        raise LocationNotFoundError()

    hostname = urlparse(origin).hostname

    if not hostname:
        raise LocationNotFoundError()

    hostname = hostname.lower()

    tenants = TenantRepository(db=db)
    locations = LocationRepository(db=db)

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

    if not tenant:
        raise LocationNotFoundError()

    location = locations.get_by_tenant_and_code(
        tenant_id=tenant.id,
        code=location_code,
    )

    if not location:
        raise LocationNotFoundError()

    return location.id