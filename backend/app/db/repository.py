from sqlalchemy.orm import Session
from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int = Field(
        default=1,
        ge=1,
    )
    limit: int = Field(
        default=25,
        ge=1,
        le=100,
    )


class Repository:
    def __init__(
        self,
        *,
        db: Session,
    ):
        self.db = db

    def _all(
        self,
        query,
        pagination: Pagination | None = None,
    ):
        if pagination is None:
            return query.all()

        return (
            query
            .offset(
                (pagination.page - 1)
                * pagination.limit
            )
            .limit(pagination.limit)
            .all()
        )
