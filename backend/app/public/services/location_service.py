from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.services import LocationServiceNotFoundError
from app.public.repositories.location_service import LocationServiceRepository
from app.public.schemas.location_service import (
    FREE_TEXT_FIELDS,
    FeaturedServiceResponse,
    LocationServiceSelectionResponse,
    LocationServiceSettingsResponse,
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
    ) -> LocationServiceSettingsResponse:
        """
        A superadmin changing what a service costs and when it runs. Prices live
        only in our database; nothing is sent to Stripe until a booking is
        paid. Only superadmins hold the permission (location_services u);
        RLS also limits writes to the location's admins (schema/0005).
        """
        config = self.location_service_repository.get_config(
            location_service_id=location_service_id,
            location_id=location_id,
        )

        if not config:
            raise LocationServiceNotFoundError()

        # Fields can't be cleared (NOT NULL), except the free text ones.
        values = {
            field: value
            for field, value in body.model_dump(exclude_unset=True).items()
            if value is not None or field in FREE_TEXT_FIELDS
        }

        # One featured service per location (uq_location_service_config_featured).
        if values.get("is_featured"):
            self.location_service_repository.unfeature_others(
                location_service_id=location_service_id,
                location_id=location_id,
                updated_by_user_id=user_id,
            )

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

        return LocationServiceSettingsResponse.model_validate(
            row,
            from_attributes=True,
        )

    def list_settings(
        self,
        *,
        location_id: UUID,
    ) -> list[LocationServiceSettingsResponse]:
        """Every service the location has, offered or not (the admin's settings)."""
        return [
            LocationServiceSettingsResponse.model_validate(row, from_attributes=True)
            for row in self.location_service_repository.list_with_context(location_id=location_id)
        ]

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

    def featured(
        self,
        *,
        location_id: UUID,
    ) -> FeaturedServiceResponse | None:
        """
        The service the centre's page leads with: the featured one if it's
        offered, else the first offered (the list's order). None when the
        location offers nothing.
        """
        offered = self.location_service_repository.list_with_context(
            location_id=location_id,
            is_active=True,
        )

        if not offered:
            return None

        chosen = next((row for row in offered if row.is_featured), offered[0])

        upcoming = self.location_service_repository.upcoming_sessions(
            location_service_id=chosen.id,
        )

        return FeaturedServiceResponse(
            location_service_id=chosen.id,
            next_session_date=upcoming.next_session_date,
            weekdays=list(upcoming.weekdays or []),
        )
