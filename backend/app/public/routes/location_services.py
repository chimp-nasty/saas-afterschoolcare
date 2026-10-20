from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission, resolve_location_id
from app.dependencies.db import get_db
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.location_service import LocationServiceService
from app.public.schemas.location_service import (
    LocationServiceSelectionResponse,
    UpdateLocationServiceConfigRequest,
)


router = APIRouter(
    prefix="/location-services/v1",
    tags=["location-services"],
)


@router.get("/public/{location_code}")
def list_public_location_services(
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: LocationServiceService = Depends(
        get_service(
            LocationServiceService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[list[LocationServiceSelectionResponse]]:
    # The landing page, before login: services and config are public.
    result = service.list_offered(
        location_id=location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched services",
        data=result,
    )


@router.patch("/{location_service_id}/config")
def update_location_service_config(
    location_service_id: UUID,
    body: UpdateLocationServiceConfigRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_services",
            action="u",
        )
    ),
    service: LocationServiceService = Depends(
        get_service(
            LocationServiceService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[LocationServiceSelectionResponse]:
    result = service.update_config(
        location_service_id=location_service_id,
        location_id=ctx.location_id,
        user_id=ctx.user_id,
        body=body,
    )

    return ApiResponse(
        ok=True,
        msg="Service updated",
        data=result,
    )


@router.get("/")
def list_location_services(
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_services",
            action="r",
        )
    ),
    service: LocationServiceService = Depends(
        get_service(
            LocationServiceService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[LocationServiceSelectionResponse]]:
    result = service.list_offered(
        location_id=ctx.location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched services",
        data=result
    )
