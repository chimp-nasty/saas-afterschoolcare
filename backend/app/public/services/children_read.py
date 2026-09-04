from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.jwt.context import TokenContext
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.children import (
    ChildResponse,
    ChildTableResponse,
    ListChildrenFilterRequest,
)


class ReadChildService:
    def __init__(self, *, db: Session, ctx: TokenContext):
        self.db = db
        self.ctx = ctx

        self.child_repository = ChildProfileRepository(db=db)

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildResponse:
        row = self.child_repository.get_with_context_by_id(
            id=id,
        )

        return ChildResponse(
            id=row.id,
            location_id=row.location_id,
            user_id=row.user_id,
            first_name=row.first_name,
            last_name=row.last_name,
            dob=row.dob,
            medical_info=row.medical_info,
            allergy_info=row.allergy_info,
            medication_info=row.medication_info,
            is_active=row.is_active,
            review_status=row.review_status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_with_filters(
        self,
        *,
        filters: ListChildrenFilterRequest,
    ) -> list[ChildTableResponse]:
        rows = self.child_repository.list_context_with_filters(
            is_active=filters.is_active,
            review_status=filters.review_status,
        )

        return [
            ChildTableResponse(
                id=row.id,
                location_id=row.location_id,
                user_id=row.user_id,
                first_name=row.first_name,
                last_name=row.last_name,
                dob=row.dob,
                is_active=row.is_active,
                review_status=row.review_status,
            )
            for row in rows
        ]