from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.children import ChildProfileNotFoundError
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.children import (
    ChildSearchResultResponse,
    ChildResponse,
    ChildTableResponse,
    ListChildrenFilterRequest,
)


class ReadChildService:
    def __init__(
        self,
        *,
        db: Session,
        child_repository: ChildProfileRepository,
    ):
        self.db = db
        self.child_repository = child_repository

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildResponse:
        row = self.child_repository.get_with_context_by_id(
            id=id,
        )

        if not row:
            raise ChildProfileNotFoundError()

        return ChildResponse.model_validate(
            row,
            from_attributes=True,
        )

    def list_with_filters(
        self,
        *,
        filters: ListChildrenFilterRequest,
    ) -> list[ChildTableResponse]:
        rows = self.child_repository.list_context_with_filters(
            is_active=filters.is_active,
            review_status=filters.review_status,
        )

        return [
            ChildTableResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]

    def search(
        self,
        *,
        location_id: UUID,
        text: str,
    ) -> list[ChildSearchResultResponse]:
        """Children whose first or last name starts with `text`, with their family (staff finding a family)."""
        return [
            ChildSearchResultResponse.model_validate(row, from_attributes=True)
            for row in self.child_repository.search(location_id=location_id, text=text.strip())
        ]
