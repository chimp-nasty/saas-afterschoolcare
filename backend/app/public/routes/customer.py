from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.auth import resolve_location_id
from app.public.services.customer import CustomerService
from app.auth.schemas.auth import (
    RegistrationRequest
)


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
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    CustomerService(db=db).onboard(
        body=body,
        location_id=location_id
    )

    return ApiResponse(
        ok=True,
        msg="Customer onboarded successfully",
        data=None,
    )