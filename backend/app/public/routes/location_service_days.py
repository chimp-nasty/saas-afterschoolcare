from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.location_service_days import LocationServiceDayService
from app.public.schemas.location_service_days import (
    ListLocationServiceDaysFilterRequest,
    LocationServiceDayTableResponse,
)


router = APIRouter(
    prefix="/location-service-days/v1",
    tags=["location-service-days"],
)


@router.get("/")
def list_location_service_days(
    filters: ListLocationServiceDaysFilterRequest = Depends(),
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_service_days",
            action="r",
        )
    ),
    service: LocationServiceDayService = Depends(
        get_service(
            LocationServiceDayService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[LocationServiceDayTableResponse]]:
    result = service.list_with_filters(
        filters=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Location Service Days",
        data=result,
    )