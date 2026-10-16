from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repository import Pagination
from app.db.transaction import transactional
from app.errors.action import (
    ActionNotFoundError
)
from app.public.schemas.action import (
    ActionResponse,
    ActionFilters,
)

from app.public.repositories.action import ActionRepository


class ReadActionService:
    def __init__(
        self,
        *,
        db: Session,
        action_repository: ActionRepository
    ):
        self.db = db
        self.action_repository = action_repository

    def list(
        self,
        *,
        filters: ActionFilters,
        pagination: Pagination,
    ) -> list[ActionResponse]:
        actions = self.action_repository.list(
            cited=filters.cited,
            user_id=filters.user_id,
            target=filters.target,
            pagination=pagination,
        )

        return [
            ActionResponse.model_validate(action)
            for action in actions
        ]

    def count_uncited(self,) -> int:
        return self.action_repository.count_uncited()

    @transactional
    def update_cited_at(
        self,
        *,
        id: UUID
    ) -> ActionResponse:
        action = self.action_repository.update_cited_at(
            id=id
        )

        if not action:
            raise ActionNotFoundError()

        return ActionResponse.model_validate(action)
