from uuid import UUID

from sqlalchemy import Date, Row, cast, func, text

from app.db.repository import Repository
from app.db.models import (
    Location,
    LocationService,
    LocationServiceConfig,
    ServiceType,
)


class LocationServiceRepository(Repository):
    """
    A location's services and their config. Both are readable by anyone
    (schema/0005), so every query filters by location itself.
    """

    def get_config(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
    ) -> LocationServiceConfig | None:
        return (
            self.db.query(LocationServiceConfig)
            .filter(
                LocationServiceConfig.location_service_id == location_service_id,
                LocationServiceConfig.location_id == location_id,
            )
            .first()
        )

    def update_config(
        self,
        *,
        config: LocationServiceConfig,
        values: dict,
        updated_by_user_id: UUID,
    ) -> LocationServiceConfig:
        for field, value in values.items():
            setattr(config, field, value)

        config.updated_by_user_id = updated_by_user_id

        self.db.flush()

        return config

    def unfeature_others(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        updated_by_user_id: UUID,
    ) -> None:
        """Before featuring a service: the location's others stop being featured."""
        (
            self.db.query(LocationServiceConfig)
            .filter(
                LocationServiceConfig.location_id == location_id,
                LocationServiceConfig.location_service_id != location_service_id,
                LocationServiceConfig.is_featured,
            )
            .update(
                {"is_featured": False, "updated_by_user_id": updated_by_user_id},
                synchronize_session="fetch",
            )
        )
        self.db.flush()

    def upcoming_sessions(
        self,
        *,
        location_service_id: UUID,
    ) -> Row:
        """(next_session_date, weekdays): public.service_upcoming_sessions."""
        return self.db.execute(
            text(
                "SELECT next_session_date, weekdays "
                "FROM public.service_upcoming_sessions(:location_service_id)"
            ),
            {"location_service_id": location_service_id},
        ).one()

    def get_child_age_limits(
        self,
        *,
        location_id: UUID,
    ) -> Row | None:
        """
        The widest age range the location's offered services accept, and
        today's date there: (min_age, max_age, today). min_age and max_age
        are None when the location offers no services.
        """
        return (
            self.db.query(
                func.min(LocationServiceConfig.min_child_age).label("min_age"),
                func.max(LocationServiceConfig.max_child_age).label("max_age"),
                cast(func.timezone(Location.timezone, func.now()), Date).label("today"),
            )
            .select_from(Location)
            .outerjoin(
                LocationServiceConfig,
                (LocationServiceConfig.location_id == Location.id)
                & LocationServiceConfig.is_active,
            )
            .filter(Location.id == location_id)
            .group_by(Location.timezone)
            .first()
        )

    def list_with_context(
        self,
        *,
        location_id: UUID,
        is_active: bool | None = None,
    ) -> list[Row]:
        query = (
            self.db.query(
                LocationService.id,
                LocationService.service_type_id,

                ServiceType.name.label("service_name"),

                LocationServiceConfig.description,
                LocationServiceConfig.current_price_cents,
                LocationServiceConfig.currency,
                LocationServiceConfig.start_time,
                LocationServiceConfig.end_time,
                LocationServiceConfig.min_child_age,
                LocationServiceConfig.max_child_age,
                LocationServiceConfig.age_label,
                LocationServiceConfig.is_featured,
                LocationServiceConfig.inclusions,
                LocationServiceConfig.drop_off_pickup,
                LocationServiceConfig.what_to_bring,
                LocationServiceConfig.activities,
                LocationServiceConfig.refund_cutoff_days,
                LocationServiceConfig.late_fee_cents,
                LocationServiceConfig.late_fee_grace_minutes,
                LocationServiceConfig.is_active,
                LocationServiceConfig.updated_at,
            )
            .join(
                ServiceType,
                ServiceType.id
                == LocationService.service_type_id,
            )
            .join(
                LocationServiceConfig,
                LocationServiceConfig.location_service_id
                == LocationService.id,
            )
            .filter(LocationService.location_id == location_id)
        )

        if is_active is not None:
            query = query.filter(
                LocationServiceConfig.is_active == is_active
            )

        return self._all(
            query.order_by(ServiceType.name.asc())
        )
