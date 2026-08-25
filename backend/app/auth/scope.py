from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuthorizationScope:
    location_id: UUID
    user_id: UUID | None