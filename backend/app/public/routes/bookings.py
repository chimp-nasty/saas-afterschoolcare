from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.bookings_create import CreateBookingService
from app.public.services.bookings_read import ReadBookingService
from app.public.schemas.booking import (
    CreateBookingRequest,
    CreateBookingResponse,
    BookingResponse,
    BookingTableResponse,
    ListBookingsFilterRequest,
    BookingConflictRow,
)


router = APIRouter(
    prefix="/booking/v1",
    tags=["booking"],
)


@router.post("/", status_code=201)
def create_booking(
    body: CreateBookingRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="c"
        )
    ),
    service: CreateBookingService = Depends(
        get_service(
            CreateBookingService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[CreateBookingResponse]:
    result = service.create(
        body=body,
        user_id=ctx.user_id,
        location_id=ctx.location_id
    )

    return ApiResponse(
        ok=True,
        msg="Created Pending Bookings",
        data=result
    )


@router.post("/conflicts")
def find_conflicts(
    body: CreateBookingRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="c",
        )
    ),
    service: CreateBookingService = Depends(
        get_service(
            CreateBookingService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[BookingConflictRow]]:
    result = service.find_conflicts(
        body=body,
    )

    return ApiResponse(
        ok=True,
        msg="Checked Booking Conflicts",
        data=result,
    )


@router.get("/{booking_id}")
def get_booking(
    booking_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="r"
        )
    ),
    service: ReadBookingService = Depends(
        get_service(
            ReadBookingService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[BookingResponse]:
    result = service.get_by_id(
        id=booking_id
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Booking",
        data=result
    )


@router.get("/")
def list_bookings(
    filters: ListBookingsFilterRequest = Depends(),
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="r"
        )
    ),
    service: ReadBookingService = Depends(
        get_service(
            ReadBookingService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[BookingTableResponse]]:
    result = service.list_with_filters(
        filters=filters
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Bookings",
        data=result
    )