from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import ChildNote


class ChildNoteRepository(Repository):
    """
    Staff's notes about children. RLS shows them to the location's staff
    and above only (never the family); the writer and creation time come
    from the session (trg_child_notes_rules).
    """

    def create(
        self,
        *,
        child_id: UUID,
        note: str,
        created_by_user_id: UUID,
    ) -> ChildNote:
        record = ChildNote(
            child_id=child_id,
            note=note,
            created_by_user_id=created_by_user_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildNote | None:
        return (
            self.db.query(ChildNote)
            .filter(ChildNote.id == id)
            .first()
        )

    def list(
        self,
        *,
        location_id: UUID,
        user_id: UUID | None = None,
        child_id: UUID | None = None,
    ) -> list[Row]:
        """A family's notes (all their children) or one child's, newest first, with the writer as "Sam L."."""
        return self.db.execute(
            text("""
                SELECT n.id, n.child_id, c.first_name AS child_first_name, n.note,
                       public.staff_short_name(n.created_by_user_id) AS created_by,
                       n.created_at
                FROM public.child_notes n
                JOIN public.child_profile c ON c.id = n.child_id
                WHERE c.location_id = :location_id
                  AND (CAST(:user_id AS uuid) IS NULL OR c.user_id = :user_id)
                  AND (CAST(:child_id AS uuid) IS NULL OR c.id = :child_id)
                ORDER BY n.created_at DESC, n.id
            """),
            {"location_id": location_id, "user_id": user_id, "child_id": child_id},
        ).all()

    def delete(
        self,
        *,
        id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete one of a family's notes; False when there's no such note."""
        deleted = self.db.execute(
            text("""
                DELETE FROM public.child_notes n
                USING public.child_profile c
                WHERE n.id = :id AND c.id = n.child_id AND c.user_id = :user_id
            """),
            {"id": id, "user_id": user_id},
        )

        return deleted.rowcount > 0
