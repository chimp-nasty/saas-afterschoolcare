from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints, model_validator


NoteText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
MessageTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]

# The pages a message can link to: the frontend's account tabs and, for a
# message about a child, that child's tabs (frontend/src/lib/navigation/tabs.ts).
ACCOUNT_LINKS = frozenset({"profile", "children", "pickups"})
CHILD_LINKS = frozenset({"profile", "manage-documents"})

MessageLink = Literal["profile", "children", "pickups", "manage-documents"]


class ChildNoteResponse(BaseModel):
    """A staff note about a child; never shown to the family."""

    id: UUID
    child_id: UUID
    child_first_name: str
    note: str
    # The writer, as "Sam L." (NULL once they no longer work here).
    created_by: str | None
    created_at: datetime


class CreateChildNoteRequest(BaseModel):
    child_id: UUID
    note: NoteText


class FamilyMessageResponse(BaseModel):
    """A message to the family, as the admin portal lists it."""

    id: UUID
    child_id: UUID | None
    child_first_name: str | None
    # The page it links to; NULL for a plain message.
    target: str | None
    title: str
    message: str
    # The writer, as "Sam L." (NULL once they no longer work here).
    created_by: str | None
    created_at: datetime
    # When the family read it.
    cited_at: datetime | None


class SendFamilyMessageRequest(BaseModel):
    title: MessageTitle
    message: NoteText
    # About one of the family's children (optional).
    child_id: UUID | None = None
    # A page in their account to link to (optional): an account page, or
    # with a child, one of that child's pages.
    target: MessageLink | None = None

    @model_validator(mode="after")
    def _link_fits(self):
        allowed = CHILD_LINKS if self.child_id else ACCOUNT_LINKS

        if self.target and self.target not in allowed:
            raise ValueError("That page can't be linked from this message")

        return self
