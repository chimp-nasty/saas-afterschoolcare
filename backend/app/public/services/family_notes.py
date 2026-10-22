import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.user import UserRepository
from app.db.transaction import transactional
from app.errors.action import ActionNotFoundError
from app.errors.children import ChildNoteNotFoundError, ChildProfileNotFoundError
from app.errors.customer import FamilyNotFoundError
from app.integrations.email.messages import NewMessageEmail
from app.integrations.email.outbox import EmailOutbox
from app.public.repositories.action import ActionRepository
from app.public.repositories.child_note import ChildNoteRepository
from app.public.repositories.family import FamilyRepository
from app.public.schemas.family_notes import (
    ChildNoteResponse,
    CreateChildNoteRequest,
    FamilyMessageResponse,
    SendFamilyMessageRequest,
)


logger = logging.getLogger("app.families")


def _child_of(family_repository: FamilyRepository, *, location_id: UUID, user_id: UUID, child_id: UUID) -> None:
    """The child must be one of this family's at this centre."""
    children = family_repository.children(location_id=location_id, user_id=user_id)

    if not any(child.id == child_id for child in children):
        raise ChildProfileNotFoundError()


def _family(family_repository: FamilyRepository, *, location_id: UUID, user_id: UUID) -> None:
    if not family_repository.get(location_id=location_id, user_id=user_id):
        raise FamilyNotFoundError()


class ChildNoteService:
    """
    Staff's notes about a family's children (slice 4-5): admins and
    superadmins write and delete them on the family's page (child_notes
    c/d), and read them there and at the staff kiosk (child_notes r, where
    staff read them too). Never shown to the family (RLS). A saved note
    can't be changed (trg_child_notes_rules): it's deleted and written again.
    """

    def __init__(
        self,
        *,
        db: Session,
        note_repository: ChildNoteRepository,
        family_repository: FamilyRepository,
    ):
        self.db = db
        self.note_repository = note_repository
        self.family_repository = family_repository

    def list_for_family(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> list[ChildNoteResponse]:
        _family(self.family_repository, location_id=location_id, user_id=user_id)

        return self._responses(self.note_repository.list(location_id=location_id, user_id=user_id))

    def list_for_child(
        self,
        *,
        location_id: UUID,
        child_id: UUID,
    ) -> list[ChildNoteResponse]:
        """One child's notes (the staff kiosk's child panel)."""
        return self._responses(self.note_repository.list(location_id=location_id, child_id=child_id))

    @transactional
    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        writer_id: UUID,
        body: CreateChildNoteRequest,
    ) -> ChildNoteResponse:
        _family(self.family_repository, location_id=location_id, user_id=user_id)
        _child_of(self.family_repository, location_id=location_id, user_id=user_id, child_id=body.child_id)

        note = self.note_repository.create(child_id=body.child_id, note=body.note, created_by_user_id=writer_id)
        self._log("child_note_added", f"child_id={body.child_id}")

        return next(
            row
            for row in self._responses(self.note_repository.list(location_id=location_id, child_id=body.child_id))
            if row.id == note.id
        )

    @transactional
    def delete(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        note_id: UUID,
    ) -> None:
        _family(self.family_repository, location_id=location_id, user_id=user_id)

        if not self.note_repository.delete(id=note_id, user_id=user_id):
            raise ChildNoteNotFoundError()

        self._log("child_note_deleted", f"note_id={note_id}")

    def _responses(self, rows) -> list[ChildNoteResponse]:
        return [ChildNoteResponse.model_validate(row, from_attributes=True) for row in rows]

    def _log(self, event: str, reason: str) -> None:
        logger.info("Child note changed", extra={"event": event, "result": "success", "reason": reason})


class FamilyMessageService:
    """
    Messages from the centre to a family (slice 4-5), on the family's page:
    the messages they've been sent and whether each was read, sending one
    (actions c), optionally about a child and linking to a page in their
    account, and withdrawing one until it's read (actions d,
    trg_actions_rules). The family reads them on /actions. Sending emails
    the account holder that there's a message; its text stays in the app
    (docs/email-policy.md).
    """

    def __init__(
        self,
        *,
        db: Session,
        action_repository: ActionRepository,
        family_repository: FamilyRepository,
        user_repository: UserRepository,
    ):
        self.db = db
        self.action_repository = action_repository
        self.family_repository = family_repository
        self.user_repository = user_repository
        self.emails = EmailOutbox(db)

    def list(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> list[FamilyMessageResponse]:
        _family(self.family_repository, location_id=location_id, user_id=user_id)

        return [
            FamilyMessageResponse.model_validate(row, from_attributes=True)
            for row in self.action_repository.list_for_family(location_id=location_id, user_id=user_id)
        ]

    @transactional
    def send(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        sender_id: UUID,
        body: SendFamilyMessageRequest,
    ) -> FamilyMessageResponse:
        _family(self.family_repository, location_id=location_id, user_id=user_id)

        if body.child_id:
            _child_of(self.family_repository, location_id=location_id, user_id=user_id, child_id=body.child_id)

        action = self.action_repository.create(
            user_id=user_id,
            location_id=location_id,
            child_id=body.child_id,
            created_by_user_id=sender_id,
            target=body.target,
            title=body.title,
            message=body.message,
        )

        # Staff outrank the family, so RLS lets them read the account holder.
        family = self.user_repository.get_by_id(id=user_id)
        self.emails.queue(NewMessageEmail(
            location_id=location_id,
            user_id=family.id,
            to_email=family.email,
            first_name=family.first_name,
        ))
        logger.info(
            "Message sent to a family",
            extra={"event": "family_message_sent", "result": "success", "reason": f"action_id={action.id}"},
        )

        return next(
            message
            for message in self.list(location_id=location_id, user_id=user_id)
            if message.id == action.id
        )

    @transactional
    def withdraw(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        message_id: UUID,
    ) -> None:
        """Delete a message the family hasn't read yet (the database refuses a read one)."""
        _family(self.family_repository, location_id=location_id, user_id=user_id)

        if not self.action_repository.delete(id=message_id, user_id=user_id):
            raise ActionNotFoundError()

        logger.info(
            "Message withdrawn",
            extra={"event": "family_message_withdrawn", "result": "success", "reason": f"action_id={message_id}"},
        )
