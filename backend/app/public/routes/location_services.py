from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.public.services.location_service import LocationServiceService
from app.public.schemas.location_service import (
    UpdateLoctionServiceRequest,
    LocationServiceSelectionResponse
)


router = APIRouter(
    prefix="/location-services/v1",
    tags=["location-services"],
)


@router.post("/update-price/{location_service_id}")
def update_price(
    stripe_product_id: str,
    body: UpdateLoctionServiceRequest,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_services",
            action="u",
        )
    )
) -> ApiResponse[None]:
    LocationServiceService(db=db).update_price(
        stripe_product_id=stripe_product_id,
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Updated product pricing",
        data=None
    )


@router.get("/list")
def list_location_services(
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="location_services",
            action="r",
        )
    )
) -> ApiResponse[list[LocationServiceSelectionResponse]]:
    result = LocationServiceService(db=db).list_all()

    return ApiResponse(
        ok=True,
        msg="Fetched services",
        data=result
    )