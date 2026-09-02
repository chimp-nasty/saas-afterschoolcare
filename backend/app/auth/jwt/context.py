from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.errors.auth import JwtInvalidError


VALID_PERMISSION_ACTIONS = {"c", "r", "u", "d"}


PermissionMap = dict[
    str,
    frozenset[str],
]


@dataclass(frozen=True)
class TokenContext:
    user_id: UUID
    location_id: UUID
    email: str | None
    first_name: str | None
    roles: tuple[str, ...]
    permissions: PermissionMap


def build_token_context(
    claims: dict[str, Any],
) -> TokenContext:
    user_id = _parse_uuid_claim(
        claims=claims,
        claim_name="user_id",
    )

    location_id = _parse_uuid_claim(
        claims=claims,
        claim_name="location_id",
    )

    roles = _parse_roles(
        claims.get("roles", []),
    )

    permissions = _parse_permissions(
        claims.get("permissions", {}),
    )

    email = _parse_optional_string(
        claims.get("email"),
    )

    first_name = _parse_optional_string(
        claims.get("first_name"),
    )

    return TokenContext(
        user_id=user_id,
        location_id=location_id,
        email=email,
        first_name=first_name,
        roles=roles,
        permissions=permissions,
    )


def _parse_uuid_claim(
    *,
    claims: dict[str, Any],
    claim_name: str,
) -> UUID:
    raw_value = claims.get(claim_name)

    if not raw_value:
        raise JwtInvalidError()

    try:
        return UUID(str(raw_value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise JwtInvalidError() from exc


def _parse_roles(
    raw_roles: Any,
) -> tuple[str, ...]:
    if not isinstance(raw_roles, list):
        raise JwtInvalidError()

    if not all(
        isinstance(role, str) and role.strip()
        for role in raw_roles
    ):
        raise JwtInvalidError()

    return tuple(
        role.strip()
        for role in raw_roles
    )


def _parse_permissions(
    raw_permissions: Any,
) -> PermissionMap:
    if not isinstance(raw_permissions, dict):
        raise JwtInvalidError()

    permissions: PermissionMap = {}

    for resource, raw_actions in raw_permissions.items():
        if not isinstance(resource, str) or not resource.strip():
            raise JwtInvalidError()

        if not isinstance(raw_actions, list):
            raise JwtInvalidError()

        if not all(
            isinstance(action, str)
            and action in VALID_PERMISSION_ACTIONS
            for action in raw_actions
        ):
            raise JwtInvalidError()

        permissions[resource.strip()] = frozenset(
            raw_actions,
        )

    return permissions


def _parse_optional_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    parsed = str(value).strip()

    return parsed or None