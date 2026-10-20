from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.refunds_create import CreateRefundService
from app.public.schemas.refunds import CreateRefundRequest, RefundResponse


router = APIRouter(
    prefix="/refunds/v1",
    tags=["refunds"],
)


@router.post("/", status_code=201)
def create_refund(
    body: CreateRefundRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="refunds",
            action="c",
        )
    ),
    service: CreateRefundService = Depends(
        get_service(
            CreateRefundService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[RefundResponse]:
    result = service.create(
        booking_id=body.booking_id,
        user_id=ctx.user_id,
        location_id=ctx.location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Refund requested",
        data=result,
    )
