from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.public.services.children_read import ReadChildService
from app.public.schemas.children import (
    ChildResponse,
    ChildTableResponse,
)


router = APIRouter(
    prefix="/children/v1",
    tags=["children"],
)


@router.get("/read/{child_id}")
def get_child(
    child_id: UUID,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="children",
            action="r",
        )
    ),
) -> ApiResponse[ChildResponse]:
    result = ReadChildService(
        db=db,
        ctx=ctx,
    ).get_by_id(
        id=child_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Child",
        data=result,
    )


@router.get("/list")
def list_children(
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="children",
            action="r",
        )
    ),
) -> ApiResponse[list[ChildTableResponse]]:
    result = ReadChildService(
        db=db,
        ctx=ctx,
    ).list_with_filters()

    return ApiResponse(
        ok=True,
        msg="Fetched Children",
        data=result,
    )