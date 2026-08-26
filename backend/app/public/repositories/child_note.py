from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.child_note import ChildNote


class ChildNoteRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        child_id: UUID,
        user_id: UUID,
        note: str,
    ) -> ChildNote:
        record = ChildNote(
            child_id=child_id,
            user_id=user_id,
            note=note,
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
