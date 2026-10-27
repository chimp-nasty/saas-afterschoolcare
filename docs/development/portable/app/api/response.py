from typing import Generic, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    ok: bool
    msg: str
    data: DataT | None = None