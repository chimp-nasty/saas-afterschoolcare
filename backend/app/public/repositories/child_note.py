from uuid import UUID

from app.db.repository import Repository
from app.public.models.child_note import ChildNote


class ChildNoteRepository(Repository):
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
