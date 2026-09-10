from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.public.services.actions_read import ReadActionService
from app.public.schemas.action import (
    ActionResponse,
)


router = APIRouter(
    prefix="/action/v1",
    tags=["action"],
)


@router.get("/")
def list_actions(
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="actions",
            action="r",
        )
    ),
) -> ApiResponse[list[ActionResponse]]:
    result = ReadActionService(db=db).list()

    return ApiResponse(
        ok=True,
        msg="Fetched Actions",
        data=result,
    )


@router.patch("/{action_id}")
def update_cited_at(
    action_id: UUID,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="actions",
            action="u",
        )
    ),
) -> ApiResponse[ActionResponse]:
    result = ReadActionService(db=db).update_cited_at(
        id=action_id
    )

    return ApiResponse(
        ok=True,
        msg="Updated Action",
        data=result
    )