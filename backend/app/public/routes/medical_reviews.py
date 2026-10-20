from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.medical_reviews_read import ReadMedicalReviewService
from app.public.services.medical_reviews_update import UpdateMedicalReviewService
from app.public.schemas.medical_reviews import (
    ListMedicalReviewsFilterRequest,
    MedicalReviewDecisionRequest,
    MedicalReviewResponse,
    MedicalReviewSummaryResponse,
)


# Staff review children's medical details (child_medical_state r / u).
# Families hold r too (to see their own child's status); RLS limits them
# to their own children here.
router = APIRouter(
    prefix="/medical-reviews/v1",
    tags=["medical-reviews"],
)


@router.get("/")
def list_medical_reviews(
    filters: Annotated[ListMedicalReviewsFilterRequest, Query()],
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_medical_state",
            action="r",
        )
    ),
    service: ReadMedicalReviewService = Depends(
        get_service(
            ReadMedicalReviewService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[MedicalReviewSummaryResponse]]:
    result = service.list_with_filters(
        filters=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Medical Reviews",
        data=result,
    )


@router.get("/{child_id}")
def get_medical_review(
    child_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_medical_state",
            action="r",
        )
    ),
    service: ReadMedicalReviewService = Depends(
        get_service(
            ReadMedicalReviewService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[MedicalReviewResponse]:
    result = service.get(
        child_id=child_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Medical Review",
        data=result,
    )


@router.post("/{child_id}")
def decide_medical_review(
    child_id: UUID,
    body: MedicalReviewDecisionRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_medical_state",
            action="u",
        )
    ),
    service: UpdateMedicalReviewService = Depends(
        get_service(
            UpdateMedicalReviewService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[MedicalReviewResponse]:
    result = service.decide(
        child_id=child_id,
        body=body,
        user_id=ctx.user_id,
    )

    return ApiResponse(
        ok=True,
        msg="Medical review updated",
        data=result,
    )
