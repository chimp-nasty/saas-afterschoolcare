from uuid import UUID

from pydantic import BaseModel, Field

from app.public.models.enums import CurrencyCode


class UpdateLoctionServiceRequest(BaseModel):
    amount_cents: int = Field(ge=0)
    currency: CurrencyCode


class LocationServiceSelectionResponse(BaseModel):
    id: UUID
    service_type_id: int

    service_name: str

    current_price_cents: int
    currency: CurrencyCode