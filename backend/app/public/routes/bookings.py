from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
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


@router("/create", status_code=201)
def create_booking(
    body: CreateBookingRequest,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="c"
        )
    )
) -> ApiResponse[CreateBookingResponse]:
    result = CreateBookingService(
        db=db,
        ctx=ctx
    ).create(
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Created Pending Bookings",
        data=result
    )


@router.post("/conflicts")
def find_conflicts(
    body: CreateBookingRequest,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="c",
        )
    ),
) -> ApiResponse[list[BookingConflictRow]]:
    result = CreateBookingService(
        db=db,
        ctx=ctx,
    ).find_conflicts(
        body=body,
    )

    return ApiResponse(
        ok=True,
        msg="Checked Booking Conflicts",
        data=result,
    )


@router.get("/read/{booking_id}")
def get_booking(
    booking_id: UUID,
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="r"
        )
    )
) -> ApiResponse[BookingResponse]:
    result = ReadBookingService(
        db=db,
        ctx=ctx
    ).get_by_id(
        id=booking_id
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Booking",
        data=result
    )


@router.get("/list")
def list_bookings(
    filters: ListBookingsFilterRequest = Depends(),
    db: Session = Depends(get_rls_db),
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="r"
        )
    )
) -> ApiResponse[list[BookingTableResponse]]:
    result = ReadBookingService(
        db=db,
        ctx=ctx
    ).list_with_filters(
        filters=filters
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Bookings",
        data=result
    )