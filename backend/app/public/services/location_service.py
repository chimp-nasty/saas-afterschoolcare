from uuid import UUID
from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.services import (
    LocationServiceNotFoundError,
    LocationServiceNotLinkedError,
)
from app.integrations.payments.stripe.client import StripeClient
from app.public.repositories.location_service import LocationServiceRepository
from app.public.schemas.location_service import (
    UpdateLocationServiceRequest,
    LocationServiceSelectionResponse,
)


class LocationServiceService:
    def __init__(
        self,
        *,
        db: Session,
        location_service_repository: LocationServiceRepository,
    ):
        self.db = db
        self.location_service_repository = location_service_repository
        self.stripe = StripeClient()

    @transactional
    def update_price(
        self,
        *,
        location_service_id: UUID,
        body: UpdateLocationServiceRequest
    ) -> None:
        # Find valid service
        location_service = (
            self.location_service_repository.get_by_id(
                id=location_service_id
            )
        )

        if not location_service:
            raise LocationServiceNotFoundError()

        if not location_service.stripe_product_id:
            raise LocationServiceNotLinkedError()

        # Create new stripe price
        stripe_price = self.stripe.create_price(
            stripe_product_id=location_service.stripe_product_id,
            amount_cents=body.amount_cents,
            currency=body.currency
        )

        # Update DB
        self.location_service_repository.update_current_price_cents(
            location_service=location_service,
            amount_cents=stripe_price.amount_cents,
            currency=stripe_price.currency
        )

    def list_all(
        self,
    ) -> list[LocationServiceSelectionResponse]:
        rows = self.location_service_repository.list_with_context(
            is_active=True
        )

        return [
            LocationServiceSelectionResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]