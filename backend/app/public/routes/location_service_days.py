from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.location_service_days import LocationServiceDayService, ManageServiceDaysService
from app.public.schemas.location_service_days import (
    CreateServiceDaysRequest,
    CreateServiceDaysResponse,
    ListLocationServiceDaysFilterRequest,
    LocationServiceDayTableResponse,
    ServiceDayOverviewFilterRequest,
    ServiceDayOverviewResponse,
    SetServiceDayCapacityRequest,
    SetServiceDayCapacityResponse,
    UpdateServiceDayRequest,
)


router = APIRouter(
    prefix="/location-service-days/v1",
    tags=["location-service-days"],
)


@router.get("/")
def list_location_service_days(
    filters: Annotated[ListLocationServiceDaysFilterRequest, Query()],
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
        user_id=ctx.user_id,
        filters=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Location Service Days",
        data=result,
    )

_manage = get_service(ManageServiceDaysService, db_dependency=get_rls_db)


# A service's days with their places, for admins (service_day_overview r:
# admins and superadmins; families book from the list above instead).
@router.get("/overview")
def get_service_day_overview(
    filters: Annotated[ServiceDayOverviewFilterRequest, Query()],
    ctx: TokenContext = Depends(require_permission(resource="service_day_overview", action="r")),
    service: ManageServiceDaysService = Depends(_manage),
) -> ApiResponse[list[ServiceDayOverviewResponse]]:
    return ApiResponse(ok=True, msg="Fetched service days", data=service.overview(location_id=ctx.location_id, filters=filters))


# Add a service's days (location_service_days c: superadmins).
@router.post("/", status_code=201)
def create_service_days(
    body: CreateServiceDaysRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_service_days", action="c")),
    service: ManageServiceDaysService = Depends(_manage),
) -> ApiResponse[CreateServiceDaysResponse]:
    result = service.create(location_id=ctx.location_id, body=body)

    return ApiResponse(ok=True, msg=f"{len(result.created)} days added", data=result)


# The same places across a date range, all or nothing (location_service_days
# u: superadmins).
@router.patch("/capacity")
def set_service_day_capacity(
    body: SetServiceDayCapacityRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_service_days", action="u")),
    service: ManageServiceDaysService = Depends(_manage),
) -> ApiResponse[SetServiceDayCapacityResponse]:
    result = service.set_capacity(location_id=ctx.location_id, body=body)

    return ApiResponse(ok=True, msg=f"{result.updated} days changed", data=result)


# One day's places, or closing or reopening it (location_service_days u:
# superadmins).
@router.patch("/{day_id}")
def update_service_day(
    day_id: UUID,
    body: UpdateServiceDayRequest,
    ctx: TokenContext = Depends(require_permission(resource="location_service_days", action="u")),
    service: ManageServiceDaysService = Depends(_manage),
) -> ApiResponse[ServiceDayOverviewResponse]:
    return ApiResponse(ok=True, msg="Day saved", data=service.update(location_id=ctx.location_id, day_id=day_id, body=body))


# Delete a day that's never been booked (location_service_days d:
# superadmins).
@router.delete("/{day_id}")
def delete_service_day(
    day_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="location_service_days", action="d")),
    service: ManageServiceDaysService = Depends(_manage),
) -> ApiResponse[None]:
    service.delete(location_id=ctx.location_id, day_id=day_id)

    return ApiResponse(ok=True, msg="Day deleted", data=None)
