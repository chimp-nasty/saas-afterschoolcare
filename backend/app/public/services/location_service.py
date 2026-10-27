import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.services import LocationServiceNotFoundError
from app.integrations.storage.client import StorageClient
from app.integrations.storage.photo_uploads import PhotoUploads, photo_version
from app.public.repositories.location_service import LocationServiceRepository
from app.public.schemas.location_service import (
    FREE_TEXT_FIELDS,
    FeaturedServiceResponse,
    LocationServiceSelectionResponse,
    LocationServiceSettingsResponse,
    UpdateLocationServiceConfigRequest,
)
from app.tenancy.schemas.site import PhotoResponse, SiteUploadResponse


logger = logging.getLogger("app.services")


def _response(model, row):
    """A service as the API returns it: its row, and its photo when it has one."""
    response = model.model_validate(row, from_attributes=True)

    if row.photo_key:
        response.photo = PhotoResponse(version=photo_version(row.photo_key), alt=row.photo_alt)

    return response


class LocationServiceService:
    def __init__(
        self,
        *,
        db: Session,
        location_service_repository: LocationServiceRepository,
    ):
        self.db = db
        self.location_service_repository = location_service_repository
        self.photos = PhotoUploads(StorageClient())

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

        return self._settings(location_service_id=location_service_id, location_id=location_id)

    def _settings(self, *, location_service_id: UUID, location_id: UUID) -> LocationServiceSettingsResponse:
        [row] = [
            row
            for row in self.location_service_repository.list_with_context(
                location_id=location_id,
            )
            if row.id == location_service_id
        ]

        return _response(LocationServiceSettingsResponse, row)

    def list_settings(
        self,
        *,
        location_id: UUID,
    ) -> list[LocationServiceSettingsResponse]:
        """Every service the location has, offered or not (the admin's settings)."""
        return [
            _response(LocationServiceSettingsResponse, row)
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

        return [_response(LocationServiceSelectionResponse, row) for row in rows]

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

    # ------------------------------------------------------------------
    # The program's photo (docs/public-site.md, stage 9b), set inline on
    # the programs page by a superadmin there (location_services u; RLS
    # limits the write to the location's admins). Keys:
    #
    #   pending/locations/{location}/services/{service}/photo/{id}
    #   branding/locations/{location}/services/{service}/photo/{id}.jpg
    # ------------------------------------------------------------------

    def _config(self, *, location_service_id: UUID, location_id: UUID):
        config = self.location_service_repository.get_config(
            location_service_id=location_service_id,
            location_id=location_id,
        )

        if not config:
            raise LocationServiceNotFoundError()

        return config

    @staticmethod
    def _photo_prefix(location_id: UUID, location_service_id: UUID) -> str:
        return f"locations/{location_id}/services/{location_service_id}/photo"

    def start_photo_upload(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        content_type: str,
    ) -> SiteUploadResponse:
        self._config(location_service_id=location_service_id, location_id=location_id)

        key, url, fields = self.photos.start(
            pending_prefix=f"pending/{self._photo_prefix(location_id, location_service_id)}",
            content_type=content_type,
            metadata={"location-id": str(location_id), "kind": "program-photo"},
        )

        return SiteUploadResponse(key=key, url=url, fields=fields)

    @transactional
    def confirm_photo_upload(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        user_id: UUID,
        key: str,
    ) -> LocationServiceSettingsResponse:
        """The uploaded photo, checked and re-saved, in place of any before."""
        config = self._config(location_service_id=location_service_id, location_id=location_id)
        prefix = self._photo_prefix(location_id, location_service_id)

        final_key = self.photos.confirm(key=key, pending_prefix=f"pending/{prefix}", final_prefix=f"branding/{prefix}")

        return self._replace_photo(config=config, values={"photo_key": final_key}, user_id=user_id)

    @transactional
    def remove_photo(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        user_id: UUID,
    ) -> LocationServiceSettingsResponse:
        """Taken off, with its description."""
        config = self._config(location_service_id=location_service_id, location_id=location_id)

        return self._replace_photo(config=config, values={"photo_key": None, "photo_alt": None}, user_id=user_id)

    def photo_url(self, *, location_service_id: UUID, location_id: UUID) -> str | None:
        """A short-lived link to the program's photo, or None when it has none."""
        config = self.location_service_repository.get_config(
            location_service_id=location_service_id,
            location_id=location_id,
        )

        return self.photos.download_url(config.photo_key) if config and config.photo_key else None

    def _replace_photo(self, *, config, values: dict, user_id: UUID) -> LocationServiceSettingsResponse:
        old_key = config.photo_key

        self.location_service_repository.update_config(config=config, values=values, updated_by_user_id=user_id)

        if old_key and old_key != config.photo_key:
            self.photos.remove(old_key)

        logger.info(
            "Program photo changed",
            extra={
                "event": "program_photo_changed",
                "result": "success",
                "reason": f"location_service_id={config.location_service_id}",
            },
        )

        return self._settings(location_service_id=config.location_service_id, location_id=config.location_id)
