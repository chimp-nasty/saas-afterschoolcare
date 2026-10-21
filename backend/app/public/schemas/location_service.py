from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.public.schemas.enums import CurrencyCode


class LocationServiceSelectionResponse(BaseModel):
    """
    One service a location offers, with everything a family sees before
    booking. Public: the landing page shows it before login.
    """

    id: UUID
    service_type_id: int

    service_name: str
    description: str | None

    current_price_cents: int
    currency: CurrencyCode

    # Session times in the location's timezone.
    start_time: time
    end_time: time

    min_child_age: int
    max_child_age: int

    refund_cutoff_days: int

    # 0 means no late fee.
    late_fee_cents: int
    late_fee_grace_minutes: int


class UpdateLocationServiceConfigRequest(BaseModel):
    """An admin's changes to a service. Only the fields sent are updated."""

    is_active: bool | None = None

    current_price_cents: int | None = Field(default=None, ge=0)
    currency: CurrencyCode | None = None

    start_time: time | None = None
    end_time: time | None = None

    description: str | None = None

    refund_cutoff_days: int | None = Field(default=None, ge=0)
    min_child_age: int | None = Field(default=None, ge=0)
    max_child_age: int | None = Field(default=None, ge=0)

    late_fee_cents: int | None = Field(default=None, ge=0)
    late_fee_grace_minutes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _blank_description_is_none(self) -> "UpdateLocationServiceConfigRequest":
        if self.description is not None:
            self.description = self.description.strip() or None

        return self


class LocationServiceSettingsResponse(LocationServiceSelectionResponse):
    """
    A service as the admin's settings show it: everything families see,
    plus whether it's offered (families only see offered ones) and when it
    was last changed.
    """

    is_active: bool
    updated_at: datetime
