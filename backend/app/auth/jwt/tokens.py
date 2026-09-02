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


class TokenService:
    @staticmethod
    def create_access_token(
        *,
        user_id: UUID,
        location_id: UUID,
        roles: list[str] | tuple[str, ...],
        permissions: PermissionMap,
        email: str | None = None,
        first_name: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)

        expires_at = now + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        )

        payload: dict[str, Any] = {
            "user_id": str(user_id),
            "location_id": str(location_id),
            "roles": list(roles),
            "permissions": {
                resource: sorted(actions)
                for resource, actions in permissions.items()
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