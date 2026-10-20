from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.services import LocationServiceNotFoundError
from app.public.repositories.location_service import LocationServiceRepository
from app.public.schemas.location_service import (
    LocationServiceSelectionResponse,
    UpdateLocationServiceConfigRequest,
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

    @transactional
    def update_config(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        user_id: UUID,
        body: UpdateLocationServiceConfigRequest,
    ) -> LocationServiceSelectionResponse:
        """
        An admin changing what a service costs and when it runs. Prices live
        only in our database; nothing is sent to Stripe until a booking is
        paid. Only admins can write the config (RLS, schema/0005).
        """
        config = self.location_service_repository.get_config(
            location_service_id=location_service_id,
            location_id=location_id,
        )

        if not config:
            raise LocationServiceNotFoundError()

        # Fields can't be cleared (NOT NULL), except the description.
        values = {
            field: value
            for field, value in body.model_dump(exclude_unset=True).items()
            if value is not None or field == "description"
        }

        if values:
            self.location_service_repository.update_config(
                config=config,
                values=values,
                updated_by_user_id=user_id,
            )

        [row] = [
            row
            for row in self.location_service_repository.list_with_context(
                location_id=location_id,
            )
            if row.id == location_service_id
        ]

        return LocationServiceSelectionResponse.model_validate(
            row,
            from_attributes=True,
        )

    def list_offered(
        self,
        *,
        location_id: UUID,
    ) -> list[LocationServiceSelectionResponse]:
        rows = self.location_service_repository.list_with_context(
            location_id=location_id,
            is_active=True,
        )

        return [
            LocationServiceSelectionResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]
