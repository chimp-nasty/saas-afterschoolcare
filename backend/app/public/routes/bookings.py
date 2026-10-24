from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission, site_origin
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.bookings_create import CreateBookingService
from app.public.services.bookings_read import ReadBookingService
from app.public.services.bookings_update import UpdateBookingService
from app.public.schemas.booking import (
    CreateBookingRequest,
    CreateBookingResponse,
    BookingGroupResponse,
    BookingGroupSummaryResponse,
    ListBookingGroupsFilterRequest,
    BookingResponse,
    BookingTableResponse,
    ListBookingsFilterRequest,
    BookingConflictRow,
    CheckoutStatusResponse,
    CheckoutUrlResponse,
)


router = APIRouter(
    prefix="/booking/v1",
    tags=["booking"],
)


@router.get("/groups")
def list_booking_groups(
    filters: Annotated[ListBookingGroupsFilterRequest, Query()],
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
) -> ApiResponse[list[BookingGroupSummaryResponse]]:
    result = service.list_groups(
        filters=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Bookings",
        data=result
    )


@router.get("/groups/{booking_group_id}")
def get_booking_group(
    booking_group_id: UUID,
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
) -> ApiResponse[BookingGroupResponse]:
    result = service.get_group(
        booking_group_id=booking_group_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Booking",
        data=result
    )


@router.post("/groups/{booking_group_id}/checkout")
def create_booking_group_checkout(
    booking_group_id: UUID,
    origin: str = Depends(site_origin),
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="u"
        )
    ),
    service: CreateBookingService = Depends(
        get_service(
            CreateBookingService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[CheckoutUrlResponse]:
    result = service.create_checkout_for_group(
        booking_group_id=booking_group_id,
        user_id=ctx.user_id,
        location_id=ctx.location_id,
        origin=origin,
    )

    return ApiResponse(
        ok=True,
        msg="Continuing to payment",
        data=result
    )


@router.post("/groups/{booking_group_id}/cancel")
def cancel_booking_group(
    booking_group_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="bookings",
            action="u"
        )
    ),
    service: UpdateBookingService = Depends(
        get_service(
            UpdateBookingService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[None]:
    service.cancel_group(
        booking_group_id=booking_group_id,
    )

    return ApiResponse(
        ok=True,
        msg="Booking cancelled",
        data=None
    )


# Cancel one paid booking without a refund, once the refund window has
# closed, until its session starts; it stays paid. bookings u: the family
# for their own, admins and superadmins for the location's families (RLS),
# with the same rules (public.booking_is_cancellable). No email.
@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="bookings", action="u")),
    service: UpdateBookingService = Depends(get_service(UpdateBookingService, db_dependency=get_rls_db)),
) -> ApiResponse[None]:
    service.cancel_booking(booking_id=booking_id)

    return ApiResponse(ok=True, msg="Booking cancelled", data=None)


# Put back a booking cancelled without a refund, until its session starts,
# if there's still a place (bookings u, as above). No email.
@router.post("/{booking_id}/reinstate")
def reinstate_booking(
    booking_id: UUID,
    ctx: TokenContext = Depends(require_permission(resource="bookings", action="u")),
    service: UpdateBookingService = Depends(get_service(UpdateBookingService, db_dependency=get_rls_db)),
) -> ApiResponse[None]:
    service.reinstate_booking(booking_id=booking_id)

    return ApiResponse(ok=True, msg="Booking reinstated", data=None)


@router.post("/", status_code=201)
def create_booking(
    body: CreateBookingRequest,
    origin: str = Depends(site_origin),
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
        location_id=ctx.location_id,
        origin=origin,
    )

    return ApiResponse(
        ok=True,
        msg="Created Pending Bookings",
        data=result
    )


@router.get("/checkout/{checkout_session_id}")
def get_checkout_status(
    checkout_session_id: str,
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
) -> ApiResponse[CheckoutStatusResponse]:
    result = service.get_checkout_status(
        checkout_session_id=checkout_session_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Checkout",
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
    filters: Annotated[ListBookingsFilterRequest, Query()],
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
        filters=filters,
        pagination=filters,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Bookings",
        data=result
    )