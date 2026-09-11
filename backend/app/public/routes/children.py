from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
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


@router.get("/{child_id}")
def get_child(
    child_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_profile",
            action="r",
        )
    ),
    service: ReadChildService = Depends(
        get_service(
            ReadChildService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ChildResponse]:
    result = service.get_by_id(
        id=child_id
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Child",
        data=result,
    )


@router.get("/")
def list_children(
    filters: ListChildrenFilterRequest = Depends(),
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_profile",
            action="r",
        )
    ),
    service: ReadChildService = Depends(
        get_service(
            ReadChildService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[ChildTableResponse]]:
    result = service.list_with_filters(
        filters=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Children",
        data=result,
    )


@router.post("/", status_code=201)
def create_child_profile(
    body: CreateChildRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_profile",
            action="c",
        )
    ),
    service: CreateChildService = Depends(
        get_service(
            CreateChildService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ChildResponse]:
    result = service.create(
        location_id=ctx.location_id,
        user_id=ctx.user_id,
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Child profile created",
        data=result
    )