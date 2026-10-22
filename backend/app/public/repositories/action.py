from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import text, update
from sqlalchemy.engine import Row

from app.db.repository import Pagination, Repository
from app.db.models import Action


class ActionRepository(Repository):
    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        created_by_user_id: UUID,
        target: str | None,
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

    def list_for_family(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> list[Row]:
        """A family's messages at a location, newest first, with the child's name and the writer as "Sam L."."""
        return self.db.execute(
            text("""
                SELECT a.id, a.child_id, c.first_name AS child_first_name, a.target,
                       a.title, a.message,
                       public.staff_short_name(a.created_by_user_id) AS created_by,
                       a.created_at, a.cited_at
                FROM public.actions a
                LEFT JOIN public.child_profile c ON c.id = a.child_id
                WHERE a.location_id = :location_id AND a.user_id = :user_id
                ORDER BY a.created_at DESC, a.id
            """),
            {"location_id": location_id, "user_id": user_id},
        ).all()

    def delete(
        self,
        *,
        id: UUID,
        user_id: UUID,
    ) -> bool:
        """Withdraw one of a family's messages; False when there's no such message."""
        deleted = self.db.execute(
            text("DELETE FROM public.actions WHERE id = :id AND user_id = :user_id"),
            {"id": id, "user_id": user_id},
        )

        return deleted.rowcount > 0
