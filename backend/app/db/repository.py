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
        pagination: Pagination | None = None,
    ):
        self.db = db
        self.pagination = pagination

    def _all(self, query):
        if self.pagination is None:
            return query.all()

        return (
            query
            .offset(
                (self.pagination.page - 1)
                * self.pagination.limit
            )
            .limit(self.pagination.limit)
            .all()
        )