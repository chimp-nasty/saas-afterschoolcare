from dataclasses import dataclass
from uuid import UUID

from fastapi import Cookie, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.jwt.tokens import TokenService
from app.core.config import settings
from app.dependencies.db import get_db
from app.errors.auth import JwtInvalidError
from app.errors.tenancy import LocationNotFoundError


# The platform's own site: the bare base domain (localhost in dev), never a
# tenant's (docs/tenant-administration.md, stage 4). Platform admins and
# registration live here; no tenant matches it, so tenant routes refuse it.
PLATFORM_COOKIE_NAME = "platform_token"


@dataclass(frozen=True)
class PlatformContext:
    platform_admin_id: UUID
    email: str


def require_platform_site(
    request: Request,
) -> None:
    """Platform and registration endpoints answer on the platform's site only."""
    if (request.url.hostname or "").lower() != settings.BASE_DOMAIN.lower():
        raise LocationNotFoundError()


def get_platform_context(
    platform_token: str | None = Cookie(default=None),
    _: None = Depends(require_platform_site),
) -> PlatformContext:
    if not platform_token:
        raise JwtInvalidError()

    claims = TokenService.decode_platform_token(platform_token)

    try:
        return PlatformContext(
            platform_admin_id=UUID(claims["sub"]),
            email=claims["email"],
        )
    except (KeyError, ValueError) as exc:
        raise JwtInvalidError() from exc


def get_platform_db(
    db: Session = Depends(get_db),
    ctx: PlatformContext = Depends(get_platform_context),
) -> Session:
    """A session acting as the platform admin (auth.is_platform_admin)."""
    db.execute(
        text("SELECT set_config('app.platform_admin_id', :id, true)"),
        {"id": str(ctx.platform_admin_id)},
    )

    return db
