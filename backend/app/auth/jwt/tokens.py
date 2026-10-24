from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
    decode,
    encode,
)

from app.auth.jwt.context import PermissionMap
from app.core.config import settings
from app.errors.auth import (
    JwtExpiredError,
    JwtInvalidError,
)


# A platform admin's token (create_platform_token). A tenant's token has
# settings.JWT_AUDIENCE or none, so neither decodes as the other.
PLATFORM_AUDIENCE = "platform"


class TokenService:
    @staticmethod
    def create_access_token(
        *,
        user_id: UUID,
        tenant_id: UUID,
        location_id: UUID | None,
        roles: list[str] | tuple[str, ...],
        permissions: PermissionMap,
        tenant_permissions: PermissionMap,
        email: str | None = None,
        first_name: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)

        expires_at = now + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        )

        payload: dict[str, Any] = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            # None in Business settings (/business), which has no location.
            "location_id": str(location_id) if location_id else None,
            "roles": list(roles),
            "permissions": {
                resource: sorted(actions)
                for resource, actions in permissions.items()
            },
            # Across the tenant, kept apart from the location's: one never
            # satisfies a check for the other.
            "tenant_permissions": {
                resource: sorted(actions)
                for resource, actions in tenant_permissions.items()
            },
            "iss": settings.JWT_ISSUER,
            "iat": now,
            "nbf": now,
            "exp": expires_at,
        }

        if settings.JWT_AUDIENCE:
            payload["aud"] = settings.JWT_AUDIENCE

        if email:
            payload["email"] = email.strip()

        if first_name:
            payload["first_name"] = first_name.strip()

        return encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def create_platform_token(
        *,
        platform_admin_id: UUID,
        email: str,
    ) -> str:
        """
        A platform admin's login (the platform's site; its own cookie). Its
        own audience and no tenant, so it never passes as a tenant's token,
        nor a tenant's token as this.
        """
        now = datetime.now(timezone.utc)

        return encode(
            {
                "sub": str(platform_admin_id),
                "email": email,
                "iss": settings.JWT_ISSUER,
                "aud": PLATFORM_AUDIENCE,
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def decode_platform_token(
        token: str,
    ) -> dict[str, Any]:
        try:
            return decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=PLATFORM_AUDIENCE,
                leeway=settings.JWT_CLOCK_SKEW_SECONDS,
            )

        except ExpiredSignatureError as exc:
            raise JwtExpiredError() from exc

        except InvalidTokenError as exc:
            raise JwtInvalidError() from exc

    @staticmethod
    def decode_access_token(
        token: str,
    ) -> dict[str, Any]:
        try:
            decode_kwargs: dict[str, Any] = {
                "jwt": token,
                "key": settings.JWT_SECRET_KEY,
                "algorithms": [
                    settings.JWT_ALGORITHM,
                ],
                "issuer": settings.JWT_ISSUER,
                "leeway": settings.JWT_CLOCK_SKEW_SECONDS,
            }

            if settings.JWT_AUDIENCE:
                decode_kwargs["audience"] = (
                    settings.JWT_AUDIENCE
                )

            claims = decode(**decode_kwargs)

            if not isinstance(claims, dict):
                raise JwtInvalidError()

            return claims

        except ExpiredSignatureError as exc:
            raise JwtExpiredError() from exc

        except JwtInvalidError:
            raise

        except InvalidTokenError as exc:
            raise JwtInvalidError() from exc