from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.public.services.children_read import ReadChildService
from app.public.services.children_create import CreateChildService
from app.public.schemas.children import (
    ChildResponse,
    ChildTableResponse,
    ListChildrenFilterRequest,
    CreateChildRequest
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
            resource="child_profile",
            action="r",
        )
    ),
) -> ApiResponse[ChildResponse]:
    result = ReadChildService(db=db).get_by_id(
        id=child_id
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Child",
        data=result,
    )


@router.get("/list")
def list_children(
    filters: ListChildrenFilterRequest = Depends(),
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_profile",
            action="r",
        )
    ),
) -> ApiResponse[list[ChildTableResponse]]:
    result = ReadChildService(db=db).list_with_filters(
        filters=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Children",
        data=result,
    )


@router.post("/create", status_code=201)
def create_child_profile(
    body: CreateChildRequest,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_profile",
            action="c",
        )
    ),
) -> ApiResponse[ChildResponse]:
    result = CreateChildService(db=db).create(
        location_id=ctx.location_id,
        user_id=ctx.user_id,
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Child profile created",
        data=result
    )