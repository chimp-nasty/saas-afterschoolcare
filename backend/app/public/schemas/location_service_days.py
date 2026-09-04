from uuid import UUID
from datetime import date

from pydantic import BaseModel


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