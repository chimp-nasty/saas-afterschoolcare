from fastapi import Query

from app.db.repository import Pagination


def get_pagination(
    page: int = Query(default=1),
    limit: int = Query(default=25),
) -> Pagination:
    return Pagination(
        page=page,
        limit=limit,
    )