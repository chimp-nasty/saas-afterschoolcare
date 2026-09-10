from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.public.models.action import Action


class ActionRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        created_by_user_id: UUID,
        target: str,
        title: str,
        message: str,
        child_id: UUID | None = None,
    ) -> Action:
        action = Action(
            user_id=user_id,
            child_id=child_id,
            target=target,
            title=title,
            message=message,
            created_by_user_id=created_by_user_id,
        )

        self.db.add(action)
        self.db.flush()

        return action

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Action | None:
        return (
            self.db.query(Action)
            .filter(Action.id == id)
            .first()
        )

    def list(self,) -> list[Action]:
        return self.db.query(Action).all()

    def update_cited_at(
        self,
        *,
        action: Action
    ) -> None:
        action.cited_at = datetime.now(timezone.utc)