from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.pickups_read import ReadPickupService
from app.public.services.pickups_create import CreatePickupService
from app.public.services.pickups_update import UpdatePickupService
from app.public.schemas.pickups import (
    CreatePickupRequest,
    PickupResponse,
    UpdatePickupRequest,
)


router = APIRouter(
    prefix="/pickups/v1",
    tags=["pickups"],
)


@router.get("/")
def list_pickups(
    ctx: TokenContext = Depends(
        require_permission(
            resource="authorized_pickup_persons",
            action="r",
        )
    ),
    service: ReadPickupService = Depends(
        get_service(
            ReadPickupService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[PickupResponse]]:
    result = service.list_active()

    return ApiResponse(
        ok=True,
        msg="Fetched Pickups",
        data=result,
    )


@router.get("/{pickup_id}")
def get_pickup(
    pickup_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="authorized_pickup_persons",
            action="r",
        )
    ),
    service: ReadPickupService = Depends(
        get_service(
            ReadPickupService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[PickupResponse]:
    result = service.get_by_id(
        id=pickup_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Pickup",
        data=result,
    )


@router.post("/", status_code=201)
def create_pickup(
    body: CreatePickupRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="authorized_pickup_persons",
            action="c",
        )
    ),
    service: CreatePickupService = Depends(
        get_service(
            CreatePickupService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[PickupResponse]:
    result = service.create(
        user_id=ctx.user_id,
        location_id=ctx.location_id,
        body=body,
    )

    return ApiResponse(
        ok=True,
        msg="Pickup person added",
        data=result,
    )


@router.patch("/{pickup_id}")
def update_pickup(
    pickup_id: UUID,
    body: UpdatePickupRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="authorized_pickup_persons",
            action="u",
        )
    ),
    service: UpdatePickupService = Depends(
        get_service(
            UpdatePickupService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[PickupResponse]:
    result = service.update(
        id=pickup_id,
        body=body,
    )

    return ApiResponse(
        ok=True,
        msg="Pickup person updated",
        data=result,
    )


@router.post("/{pickup_id}/deactivate")
def deactivate_pickup(
    pickup_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="authorized_pickup_persons",
            action="d",
        )
    ),
    service: UpdatePickupService = Depends(
        get_service(
            UpdatePickupService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[PickupResponse]:
    result = service.deactivate(
        id=pickup_id,
    )

    return ApiResponse(
        ok=True,
        msg="Pickup person removed",
        data=result,
    )
