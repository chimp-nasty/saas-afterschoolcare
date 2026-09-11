from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.actions_read import ReadActionService
from app.public.schemas.action import ActionResponse, ActionFilters


router = APIRouter(
    prefix="/action/v1",
    tags=["action"],
)


@router.get("/")
def list_actions(
    filters: ActionFilters = Depends(),
    ctx: TokenContext = Depends(
        require_permission(
            resource="actions",
            action="r",
        )
    ),
    service: ReadActionService = Depends(
        get_service(
            ReadActionService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[ActionResponse]]:
    result = service.list(
        filters=filters
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Actions",
        data=result,
    )


@router.get("/count/uncited")
def count_uncited(
    ctx: TokenContext = Depends(
        require_permission(
            resource="actions",
            action="r",
        )
    ),
    service: ReadActionService = Depends(
        get_service(
            ReadActionService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[int]:
    result = service.count_uncited()

    return ApiResponse(
        ok=True,
        msg="Fetched uncited actions",
        data=result,
    )


@router.patch("/{action_id}")
def update_cited_at(
    action_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="actions",
            action="u",
        )
    ),
    service: ReadActionService = Depends(
        get_service(
            ReadActionService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ActionResponse]:
    result = service.update_cited_at(
        id=action_id,
    )

    return ApiResponse(
        ok=True,
        msg="Updated Action",
        data=result,
    )