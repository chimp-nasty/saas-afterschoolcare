from datetime import date, datetime, time
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
    # Shown instead of "Ages X–Y" when set (e.g. "Years 7 to 12").
    age_label: str | None

    # The one the centre's page leads with (at most one per location).
    is_featured: bool

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
    # Blank clears it (back to "Ages X–Y").
    age_label: str | None = Field(default=None, max_length=40)

    # True makes this the centre page's service, in place of any other.
    is_featured: bool | None = None

    late_fee_cents: int | None = Field(default=None, ge=0)
    late_fee_grace_minutes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _blank_text_is_none(self) -> "UpdateLocationServiceConfigRequest":
        if self.description is not None:
            self.description = self.description.strip() or None

        if self.age_label is not None:
            self.age_label = self.age_label.strip() or None

        return self


class FeaturedServiceResponse(BaseModel):
    """
    The service a centre's page leads with (docs/public-site.md): the
    featured one, else the first offered. Its details are in the services
    list (same id). Public: the page shows it before login.
    """

    location_service_id: UUID

    # The next open session that hasn't finished, in the location's time;
    # None when none are set up.
    next_session_date: date | None

    # The weekdays its open sessions fall on over the next four weeks
    # (1 Monday to 7 Sunday), for "Mon–Fri".
    weekdays: list[int]


class LocationServiceSettingsResponse(LocationServiceSelectionResponse):
    """
    A service as the admin's settings show it: everything families see,
    plus whether it's offered (families only see offered ones) and when it
    was last changed.
    """

    is_active: bool
    updated_at: datetime
