from uuid import UUID
from datetime import date, timedelta

from pydantic import BaseModel, Field, field_validator, model_validator


# The most days one request covers (a year of a service).
MAX_RANGE_DAYS = 366


class ListLocationServiceDaysFilterRequest(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    is_open: bool | None = None


class LocationServiceDayTableResponse(BaseModel):
    id: UUID
    location_service_id: UUID
    service_type_id: int

    service_name: str
    service_date: date

    is_open: bool
    capacity: int

    # Places left for anyone (every family's live bookings counted).
    places_left: int

    # The caller's own children already booked this day.
    booked_child_ids: list[UUID]

    # Today or earlier, location time: can't be booked.
    is_past: bool

def _range_ok(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise ValueError("The end date must be on or after the start date")

    if date_to - date_from > timedelta(days=MAX_RANGE_DAYS):
        raise ValueError(f"Choose at most {MAX_RANGE_DAYS} days at a time")


class ServiceDayOverviewFilterRequest(BaseModel):
    location_service_id: UUID
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def _range(self):
        _range_ok(self.date_from, self.date_to)
        return self


class ServiceDayOverviewResponse(BaseModel):
    """One service day as admins see it: open or closed, and its places."""

    id: UUID
    service_date: date
    is_open: bool
    closed_reason: str | None

    capacity: int
    # Confirmed bookings (the children on the run sheet).
    booked: int
    # Places held by bookings still awaiting payment.
    awaiting_payment: int
    # What families can still book.
    places_left: int

    # Ever booked (even if since cancelled): it can be closed, not deleted.
    ever_booked: bool
    # Before today, location time: shown, not changed.
    is_past: bool


class CreateServiceDaysRequest(BaseModel):
    """
    Add a service's days: every chosen weekday from date_from to date_to
    (one day: the same date for both). Days that already exist are skipped.
    """

    location_service_id: UUID
    date_from: date
    date_to: date
    # 0 = Monday ... 6 = Sunday; all days when left out.
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)))
    capacity: int = Field(ge=0, le=1000)

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, value: list[int]) -> list[int]:
        if not value or any(day < 0 or day > 6 for day in value):
            raise ValueError("Choose at least one weekday")

        return sorted(set(value))

    @model_validator(mode="after")
    def _range(self):
        _range_ok(self.date_from, self.date_to)
        return self


class CreateServiceDaysResponse(BaseModel):
    created: list[date]
    # Already there (left as they were).
    skipped: list[date]


class UpdateServiceDayRequest(BaseModel):
    """Change one day: its places, open or closed, and why it's closed."""

    capacity: int | None = Field(default=None, ge=0, le=1000)
    is_open: bool | None = None
    closed_reason: str | None = Field(default=None, max_length=200)

    @field_validator("closed_reason")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None


class SetServiceDayCapacityRequest(BaseModel):
    """The same places for every day of a service in a date range."""

    location_service_id: UUID
    date_from: date
    date_to: date
    capacity: int = Field(ge=0, le=1000)

    @model_validator(mode="after")
    def _range(self):
        _range_ok(self.date_from, self.date_to)
        return self


class SetServiceDayCapacityResponse(BaseModel):
    updated: int
