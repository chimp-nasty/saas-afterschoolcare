from uuid import UUID

from pydantic import BaseModel


class ChildResponse(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str


class ChildTableResponse(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str


class ListChildrenFilterRequest(BaseModel):
    is_active: bool | None = None
    review_status: list[str] | None = None