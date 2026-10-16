from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repository import Pagination
from app.errors.bookings import BookingNotFoundError
from app.public.repositories.booking import BookingRepository
from app.public.schemas.booking import (
    BookingResponse,
    BookingTableResponse,
    ListBookingsFilterRequest
)


class ReadBookingService:
    def __init__(
        self,
        *,
        db: Session,
        booking_repository: BookingRepository,
    ):
        self.db = db
        self.booking_repository = booking_repository

    def get_by_id(
        self,
        *,
        id: UUID
    ) -> BookingResponse:
        row = self.booking_repository.get_with_context_by_id(
            id=id
        )

        if not row:
            raise BookingNotFoundError()

        return BookingResponse.model_validate(
            row,
            from_attributes=True,
        )

    def list_with_filters(
        self,
        *,
        filters: ListBookingsFilterRequest,
        pagination: Pagination,
    ) -> list[BookingTableResponse]:
        rows = self.booking_repository.list_context_with_filters(
            booking_status=filters.booking_status,
            payment_status=filters.payment_status,
            date_from=filters.date_from,
            date_to=filters.date_to,
            pagination=pagination,
        )

        return [
            BookingTableResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]
