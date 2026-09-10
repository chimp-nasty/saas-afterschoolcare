from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.action import (
    ActionNotFoundError
)
from app.public.schemas.action import (
    ActionResponse,
)

from app.public.repositories.action import ActionRepository


class ReadActionService:
    def __init__(self, *, db: Session):
        self.db = db

        self.action_repository = ActionRepository(db=db)

    def list(self,) -> list[ActionResponse]:
        actions = self.action_repository.list()

        return [
            ActionResponse.model_validate(action)
            for action in actions
        ]

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