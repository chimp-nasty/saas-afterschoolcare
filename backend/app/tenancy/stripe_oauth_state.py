"""
The `state` carried through "Connect with Stripe" (Stripe's OAuth for
linking an existing account). Stripe returns everyone to one registered
address on the API, so the state says who started it, for which tenant,
and which site to send them back to. Signed like the app's tokens but with
its own audience, so it can't be used as anything else, and it lasts only
long enough to log in to Stripe and approve.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jwt import InvalidTokenError, decode, encode

from app.core.config import settings


_AUDIENCE = "stripe-connect-oauth"
_LIFETIME = timedelta(minutes=30)


@dataclass(frozen=True)
class OAuthState:
    user_id: UUID
    tenant_id: UUID
    # Business settings on the tenant's site, checked when it was issued
    # (app/tenancy/site_url.py).
    site_url: str


def encode_state(state: OAuthState) -> str:
    now = datetime.now(timezone.utc)

    return encode(
        {
            "sub": str(state.user_id),
            "tenant": str(state.tenant_id),
            "site": state.site_url,
            "iss": settings.JWT_ISSUER,
            "aud": _AUDIENCE,
            "iat": now,
            "nbf": now,
            "exp": now + _LIFETIME,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_state(token: str) -> OAuthState | None:
    """The state, or None if it's forged, expired or not ours."""
    try:
        claims = decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )

        return OAuthState(
            user_id=UUID(claims["sub"]),
            tenant_id=UUID(claims["tenant"]),
            site_url=claims["site"],
        )
    except (InvalidTokenError, KeyError, ValueError):
        return None
