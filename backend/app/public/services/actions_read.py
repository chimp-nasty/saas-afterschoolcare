from uuid import UUID

from sqlalchemy.orm import Session

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
        filters: ActionFilters
    ) -> list[ActionResponse]:
        actions = self.action_repository.list(
            cited=filters.cited,
            user_id=filters.user_id,
            target=filters.target
        )

        return [
            ActionResponse.model_validate(action)
            for action in actions
        ]

    def count_uncited(self,) -> int:
        return self.action_repository.count_uncited()

    def update_cited_at(
        self,
        *,
        id: UUID
    ) -> ActionResponse:
        try:
            action = self.action_repository.get_by_id(
                id=id
            )

            if not action:
                raise ActionNotFoundError()

            self.action_repository.update_cited_at(
                action=action
            )

            self.db.flush()
            self.db.refresh(action)

            result = ActionResponse.model_validate(action)

            self.db.commit()

            return result

        except Exception:
            self.db.rollback()
            raise