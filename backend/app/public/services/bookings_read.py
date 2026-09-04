from uuid import UUID
from datetime import date

from sqlalchemy.orm import Session

from app.auth.jwt.context import TokenContext
from app.public.repositories.booking import BookingRepository
from app.public.schemas.booking import (
    BookingResponse,
    BookingTableResponse,
    ListBookingsFilterRequest
)


class ReadBookingService:
    def __init__(self, *, db: Session, ctx: TokenContext):
        self.db = db
        self.ctx = ctx

        self.booking_repository = BookingRepository(db=db)

    def get_by_id(
        self,
        *,
        id: UUID
    ) -> BookingResponse:
        row = self.booking_repository.get_with_context_by_id(
            id=id
        )

        return BookingResponse(
            id=row.id,
            location_id=row.location_id,
            user_id=row.user_id,
            booking_group_id=row.booking_group_id,
            location_service_day_id=row.location_service_day_id,
            child_id=row.child_id,
            child_name=f"{row.first_name} {row.last_name}",
            service_date=row.service_date,
            service_name=row.service_name,
            booking_status=row.booking_status,
            payment_status=row.payment_status,
            cancelled_at=row.cancelled_at,
            price_snapshot_cents=row.price_snapshot_cents,
            currency=row.currency,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_with_filters(
        self,
        *,
        filters: ListBookingsFilterRequest,
    ) -> list[BookingTableResponse]:
        rows = self.booking_repository.list_context_with_filters(
            booking_status=filters.booking_status,
            payment_status=filters.payment_status,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )

        return [
            BookingTableResponse(
                id=row.id,
                location_id=row.location_id,
                user_id=row.user_id,
                booking_group_id=row.booking_group_id,
                location_service_day_id=row.location_service_day_id,
                child_id=row.child_id,
                child_name=f"{row.first_name} {row.last_name}",
                service_date=row.service_date,
                service_name=row.service_name,
                booking_status=row.booking_status,
                payment_status=row.payment_status,
            )
            for row in rows
        ]