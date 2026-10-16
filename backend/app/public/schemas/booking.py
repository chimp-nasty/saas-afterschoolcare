from uuid import UUID
from datetime import date, datetime

from pydantic import BaseModel

from app.db.repository import Pagination


class BookingSelection(BaseModel):
    child_id: UUID
    location_service_days: list[UUID]


class CreateBookingRequest(BaseModel):
    idempotency_key: str
    bookings: list[BookingSelection]


class CreateBookingResponse(BaseModel):
    idempotency_key: str
    amount: int
    booking_group_id: UUID


class BookingConflictRow(BaseModel):
    child_id: UUID
    child_name: str

    location_service_day_id: UUID
    location_service_date: date


# Inherits page/limit: FastAPI only expands a query model when it's the
# route's only query parameter.
class ListBookingsFilterRequest(Pagination):
    booking_status: list[str] | None = None
    payment_status: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None


class BookingResponse(BaseModel):
    id: UUID
    location_id: UUID
    user_id: UUID
    booking_group_id: UUID
    location_service_day_id: UUID
    child_id: UUID

    child_name: str
    service_date: date
    service_name: str

    booking_status: str
    payment_status: str
    cancelled_at: datetime | None

    price_snapshot_cents: int
    currency: str

    created_at: datetime
    updated_at: datetime


class BookingTableResponse(BaseModel):
    id: UUID
    location_id: UUID
    user_id: UUID
    booking_group_id: UUID
    location_service_day_id: UUID
    child_id: UUID

    child_name: str
    service_date: date
    service_name: str

    booking_status: str
    payment_status: str
