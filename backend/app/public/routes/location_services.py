from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.location_service import LocationServiceService
from app.public.schemas.location_service import (
    UpdateLoctionServiceRequest,
    LocationServiceSelectionResponse
)


router = APIRouter(
    prefix="/location-services/v1",
    tags=["location-services"],
)


@router.patch("/{location_service_id}/price")
def update_price(
    stripe_product_id: str,
    body: UpdateLoctionServiceRequest,
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
) -> ApiResponse[None]:
    service.update_price(
        stripe_product_id=stripe_product_id,
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Updated product pricing",
        data=None
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
    result = service.list_all()

    return ApiResponse(
        ok=True,
        msg="Fetched services",
        data=result
    )