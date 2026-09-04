from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.jwt.context import TokenContext
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.children import (
    ChildResponse,
    ChildTableResponse,
)


class ReadChildService:
    def __init__(self, *, db: Session, ctx: TokenContext):
        self.db = db
        self.ctx = ctx

        self.child_repository = ChildProfileRepository(db=db)

    def get_by_id(
        self,
        *,
        id: UUID
    ) -> ChildResponse:
        ...

    def list_with_filters(
        self,
    ) -> ChildTableResponse:
        ...