from uuid import UUID
from sqlalchemy.orm import Session

from app.errors.services import LocationServiceNotFoundError
from app.integrations.payments.stripe.client import StripeClient
from app.public.repositories.location_service import LocationServiceRepository
from app.public.schemas.location_service import (
    UpdateLoctionServiceRequest,
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

    def update_price(
        self,
        *,
        location_service_id: UUID,
        body: UpdateLoctionServiceRequest
    ) -> None:
        try:
            # Find valid service
            location_service = (
                self.location_service_repository.get_by_id(
                    id=location_service_id
                )
            )

            if not location_service:
                raise LocationServiceNotFoundError()

            # Create new stripe price
            stripe_price = self.stripe.create_price(
                stripe_product_id=body.stripe_product_id,
                amount_cents=body.amount_cents,
                currency=body.currency
            )

            # Update DB
            self.location_service_repository.update_current_price_cents(
                location_service=location_service,
                amount_cents=stripe_price.amount_cents,
                currency=stripe_price.currency
            )

            self.db.commit()
        
        except Exception:
            self.db.rollback()
            raise

    def list_all(
        self,
    ) -> list[LocationServiceSelectionResponse]:
        rows = self.location_service_repository.list_with_context(
            is_active=True
        )

        return [
            LocationServiceSelectionResponse(
                id=row.id,
                service_type_id=row.service_type_id,
                service_name=row.service_name,
                current_price_cents=row.current_price_cents,
                currency=row.currency,
            )
            for row in rows
        ]