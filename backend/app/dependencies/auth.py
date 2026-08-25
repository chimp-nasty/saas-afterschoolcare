from collections.abc import Callable
from uuid import UUID

from fastapi import Cookie
from fastapi import Depends

from app.authorization.jwt.context import (
    TokenContext,
    build_token_context,
)
from app.authorization.jwt.tokens import TokenService
from app.authorization.scope import AuthorizationScope
from app.errors.auth import PermissionNotFoundError, JwtInvalidError


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