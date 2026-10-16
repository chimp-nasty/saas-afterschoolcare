from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import update

from app.db.repository import Pagination, Repository
from app.db.models import Action


class ActionRepository(Repository):
    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        created_by_user_id: UUID,
        target: str,
        title: str,
        message: str,
        child_id: UUID | None = None,
    ) -> Action:
        action = Action(
            user_id=user_id,
            location_id=location_id,
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

    def update_cited_at(
        self,
        *,
        id: UUID,
    ) -> Action | None:
        stmt = (
            update(Action)
            .where(Action.id == id)
            .values(cited_at=datetime.now(timezone.utc))
            .returning(Action)
        )

        result = self.db.execute(stmt)

        return result.scalar_one_or_none()

    def count_uncited(self,) -> int:
        return (
            self.db.query(Action)
            .filter(Action.cited_at.is_(None))
            .count()
        )

    def list(
        self,
        *,
        cited: bool | None = None,
        user_id: UUID | None = None,
        target: str | None = None,
        pagination: Pagination | None = None,
    ) -> list[Action]:
        query = self.db.query(Action)

        if cited is True:
            query = query.filter(
                Action.cited_at.is_not(None)
            )
        elif cited is False:
            query = query.filter(
                Action.cited_at.is_(None)
            )

        if user_id is not None:
            query = query.filter(
                Action.user_id == user_id
            )

        if target is not None:
            query = query.filter(
                Action.target == target
            )

        query = query.order_by(
            Action.created_at.desc(),
            Action.id.desc(),
        )

        return self._all(query, pagination)