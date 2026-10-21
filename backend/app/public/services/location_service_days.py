import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.services import (
    LocationServiceNotFoundError,
    ServiceDayCapacityBelowBookedError,
    ServiceDayNotFoundError,
)
from app.public.repositories.location_service import LocationServiceRepository
from app.public.repositories.location_service_day import LocationServiceDayRepository
from app.public.schemas.location_service_days import (
    CreateServiceDaysRequest,
    CreateServiceDaysResponse,
    ListLocationServiceDaysFilterRequest,
    LocationServiceDayTableResponse,
    ServiceDayOverviewFilterRequest,
    ServiceDayOverviewResponse,
    SetServiceDayCapacityRequest,
    SetServiceDayCapacityResponse,
    UpdateServiceDayRequest,
)


logger = logging.getLogger("app.services")


class LocationServiceDayService:
    def __init__(
        self,
        *,
        db: Session,
        location_service_repository: LocationServiceDayRepository,
    ):
        self.db = db

        self.location_service_repository = (
            location_service_repository
        )

    def list_with_filters(
        self,
        *,
        user_id: UUID,
        filters: ListLocationServiceDaysFilterRequest,
    ) -> list[LocationServiceDayTableResponse]:
        rows = (
            self.location_service_repository
            .list_context_with_filters(
                user_id=user_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                is_open=filters.is_open,
            )
        )

        return [
            LocationServiceDayTableResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]


class ManageServiceDaysService:
    """
    A location's service days as admins run them: seeing each day's places,
    and (superadmins, by permission) adding days, changing places, closing,
    reopening and deleting them. The database keeps bookings safe whoever
    does it (trg_location_service_days_rules): no days in the past, places
    never below what's booked, no closing a booked day, no deleting a day
    that's ever been booked.
    """

    def __init__(
        self,
        *,
        db: Session,
        day_repository: LocationServiceDayRepository,
        service_repository: LocationServiceRepository,
    ):
        self.db = db
        self.day_repository = day_repository
        self.service_repository = service_repository

    def overview(
        self,
        *,
        location_id: UUID,
        filters: ServiceDayOverviewFilterRequest,
    ) -> list[ServiceDayOverviewResponse]:
        self._service(location_service_id=filters.location_service_id, location_id=location_id)

        return [
            ServiceDayOverviewResponse.model_validate(row, from_attributes=True)
            for row in self.day_repository.overview(
                location_service_id=filters.location_service_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
            )
        ]

    @transactional
    def create(
        self,
        *,
        location_id: UUID,
        body: CreateServiceDaysRequest,
    ) -> CreateServiceDaysResponse:
        self._service(location_service_id=body.location_service_id, location_id=location_id)

        dates = [
            body.date_from + timedelta(days=offset)
            for offset in range((body.date_to - body.date_from).days + 1)
            if (body.date_from + timedelta(days=offset)).weekday() in body.weekdays
        ]
        created = self.day_repository.create_many(
            location_service_id=body.location_service_id,
            location_id=location_id,
            dates=dates,
            capacity=body.capacity,
        )

        self._log("service_days_added", f"location_service_id={body.location_service_id}; added={len(created)}")

        return CreateServiceDaysResponse(created=created, skipped=sorted(set(dates) - set(created)))

    @transactional
    def update(
        self,
        *,
        location_id: UUID,
        day_id: UUID,
        body: UpdateServiceDayRequest,
    ) -> ServiceDayOverviewResponse:
        day = self._day(day_id=day_id, location_id=location_id)
        values = body.model_dump(exclude_unset=True)

        # Only a closed day has a reason.
        if values.get("is_open", day.is_open):
            values.pop("closed_reason", None)

        if "capacity" in values and values["capacity"] < day.capacity:
            held = self.day_repository.places_held(id=day.id)

            if values["capacity"] < held:
                raise ServiceDayCapacityBelowBookedError(
                    message=f"{held} places are booked, so places can't go below {held}",
                )

        self.day_repository.update(day=day, values=values)
        self._log("service_day_updated", f"day_id={day.id}; changes={sorted(values)}")

        return self._overview_of(day)

    @transactional
    def set_capacity(
        self,
        *,
        location_id: UUID,
        body: SetServiceDayCapacityRequest,
    ) -> SetServiceDayCapacityResponse:
        self._service(location_service_id=body.location_service_id, location_id=location_id)

        # All or nothing, naming the days that are booked past the new places.
        over = self.day_repository.held_above(
            location_service_id=body.location_service_id,
            date_from=body.date_from,
            date_to=body.date_to,
            capacity=body.capacity,
        )

        if over:
            days = ", ".join(f"{row.service_date.strftime('%a %d %b')} ({row.held})" for row in over)
            raise ServiceDayCapacityBelowBookedError(
                message=f"These days have more places booked than {body.capacity}: {days}",
            )

        updated = self.day_repository.set_capacity(
            location_service_id=body.location_service_id,
            date_from=body.date_from,
            date_to=body.date_to,
            capacity=body.capacity,
        )
        self._log("service_days_capacity_set", f"location_service_id={body.location_service_id}; days={updated}")

        return SetServiceDayCapacityResponse(updated=updated)

    @transactional
    def delete(
        self,
        *,
        location_id: UUID,
        day_id: UUID,
    ) -> None:
        day = self._day(day_id=day_id, location_id=location_id)
        self.day_repository.delete(day=day)
        self._log("service_day_deleted", f"day_id={day_id}")

    def _service(self, *, location_service_id: UUID, location_id: UUID) -> None:
        if not self.service_repository.get_config(location_service_id=location_service_id, location_id=location_id):
            raise LocationServiceNotFoundError()

    def _day(self, *, day_id: UUID, location_id: UUID):
        # RLS: only the session's location's days.
        day = self.day_repository.get_by_id(id=day_id)

        if not day or day.location_id != location_id:
            raise ServiceDayNotFoundError()

        return day

    def _overview_of(self, day) -> ServiceDayOverviewResponse:
        [row] = self.day_repository.overview(
            location_service_id=day.location_service_id,
            date_from=day.service_date,
            date_to=day.service_date,
        )

        return ServiceDayOverviewResponse.model_validate(row, from_attributes=True)

    def _log(self, event: str, reason: str) -> None:
        logger.info("Service days changed", extra={"event": event, "result": "success", "reason": reason})
