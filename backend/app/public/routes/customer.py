from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.rls import get_rls_db
from app.dependencies.auth import resolve_location_id, require_permission
from app.dependencies.service import get_service
from app.auth.jwt.context import TokenContext
from app.public.services.customer import CustomerService
from app.auth.schemas.auth import RegistrationRequest
from app.public.schemas.customer import CustomerProfileResponse, UpdateCustomerProfileRequest


router = APIRouter(
    prefix="/customer/v1",
    tags=["customer"],
)


@router.post("/onboard/{location_code}", status_code=201)
def onboard(
    body: RegistrationRequest,
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: CustomerService = Depends(
        get_service(
            CustomerService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    service.onboard(
        body=body,
        location_id=location_id
    )

    return ApiResponse(
        ok=True,
        msg="Customer onboarded successfully",
        data=None,
    )


@router.patch("/profile")
def update_profile(
    body: UpdateCustomerProfileRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="customer_profile",
            action="u",
        )
    ),
    service: CustomerService = Depends(
        get_service(
            CustomerService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[CustomerProfileResponse]:
    result = service.update(
        user_id=ctx.user_id,
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Updated profile",
        data=result
    )


@router.get("/profile")
def get_profile(
    ctx: TokenContext = Depends(
        require_permission(
            resource="customer_profile",
            action="r",
        )
    ),
    service: CustomerService = Depends(
        get_service(
            CustomerService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[CustomerProfileResponse]:
    result = service.get(
        user_id=ctx.user_id
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Profile",
        data=result
    )