from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.repository import Pagination


class ActionResponse(BaseModel):
    id: UUID

    user_id: UUID
    child_id: UUID | None

    target: str

    title: str
    message: str

    created_by_user_id: UUID

    created_at: datetime
    cited_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# Inherits page/limit: FastAPI only expands a query model when it's the
# route's only query parameter.
class ActionFilters(Pagination):
    cited: bool | None = None
    user_id: UUID | None = None
    target: str | None = None