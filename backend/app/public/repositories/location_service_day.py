from uuid import UUID
from datetime import date

from sqlalchemy import Date, Integer, String, cast, exists, func, literal, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import (
    Booking,
    Location,
    LocationService,
    LocationServiceConfig,
    LocationServiceDay,
    ServiceType,
)


class LocationServiceDayRepository(Repository):
    def create(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        service_date,
        capacity: int,
        is_open: bool = True,
    ) -> LocationServiceDay:
        record = LocationServiceDay(
            location_service_id=location_service_id,
            location_id=location_id,
            service_date=service_date,
            capacity=capacity,
            is_open=is_open,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> LocationServiceDay | None:
        return (
            self.db.query(LocationServiceDay)
            .filter(LocationServiceDay.id == id)
            .first()
        )

    def list_by_service_day_ids(
        self,
        *,
        ids: list[UUID],
    ) -> list[Row]:
        return (
            self.db.query(
                LocationServiceDay.id.label(
                    "location_service_day_id"
                ),
                LocationServiceDay.service_date,
                LocationServiceDay.capacity,

                LocationService.id.label(
                    "location_service_id"
                ),

                LocationServiceConfig.current_price_cents,
                LocationServiceConfig.currency,

                ServiceType.name.label("service_name"),
            )
            .join(
                LocationService,
                LocationService.id
                == LocationServiceDay.location_service_id,
            )
            .join(
                LocationServiceConfig,
                LocationServiceConfig.location_service_id
                == LocationService.id,
            )
            .join(
                ServiceType,
                ServiceType.id
                == LocationService.service_type_id,
            )
            .filter(
                LocationServiceDay.id.in_(ids),
            )
            .order_by(
                LocationServiceDay.id,
            )
            # Lock only the days being booked (capacity), not the shared
            # service, config and service type rows every booking joins
            # through.
            .with_for_update(of=LocationServiceDay)
            .all()
        )

    def list_context_with_filters(
        self,
        *,
        user_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        is_open: bool | None = None,
    ) -> list[Row]:
        # This family's children already booked that day (pending or
        # confirmed, not a lapsed hold). Filtered by user as well as RLS, so
        # staff calling this don't get every family's children. Text, as
        # psycopg2 doesn't parse uuid arrays.
        booked_child_ids = (
            select(
                func.coalesce(
                    func.array_agg(func.distinct(cast(Booking.child_id, String))),
                    cast(literal("{}"), ARRAY(String)),
                )
            )
            .where(
                Booking.location_service_day_id == LocationServiceDay.id,
                Booking.user_id == user_id,
                func.public.effective_booking_status(
                    Booking.booking_status,
                    Booking.created_at,
                    type_=Booking.__table__.c.booking_status.type,
                ).in_(["PENDING", "CONFIRMED"]),
            )
            .correlate(LocationServiceDay)
            .scalar_subquery()
        )

        # Today and earlier can't be booked (schema/0008), in the location's
        # own timezone.
        location_today = cast(func.timezone(Location.timezone, func.now()), Date)

        query = (
            self.db.query(
                LocationServiceDay.id,
                LocationServiceDay.location_service_id,
                LocationService.service_type_id,

                ServiceType.name.label("service_name"),

                LocationServiceDay.service_date,
                LocationServiceDay.is_open,
                LocationServiceDay.capacity,

                func.public.service_day_places_left(LocationServiceDay.id).label("places_left"),
                booked_child_ids.label("booked_child_ids"),
                (LocationServiceDay.service_date <= location_today).label("is_past"),
            )
            .join(
                LocationService,
                LocationService.id
                == LocationServiceDay.location_service_id,
            )
            .join(
                ServiceType,
                ServiceType.id
                == LocationService.service_type_id,
            )
            .join(
                Location,
                Location.id == LocationServiceDay.location_id,
            )
        )

        if date_from:
            query = query.filter(
                LocationServiceDay.service_date >= date_from
            )

        if date_to:
            query = query.filter(
                LocationServiceDay.service_date <= date_to
            )

        if is_open is not None:
            query = query.filter(
                LocationServiceDay.is_open == is_open
            )

        return self._all(
            query.order_by(
                LocationServiceDay.service_date.asc(),
                LocationServiceDay.id.asc(),
            )
        )

    def overview(
        self,
        *,
        location_service_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[Row]:
        """A service's days in a range, with their places (RLS: the location's)."""
        held = func.public.service_day_places_held(LocationServiceDay.id)
        booked = (
            select(func.count(Booking.id))
            .where(
                Booking.location_service_day_id == LocationServiceDay.id,
                Booking.booking_status == "CONFIRMED",
            )
            .correlate(LocationServiceDay)
            .scalar_subquery()
        )
        ever_booked = exists().where(Booking.location_service_day_id == LocationServiceDay.id)
        location_today = cast(func.timezone(Location.timezone, func.now()), Date)

        return (
            self.db.query(
                LocationServiceDay.id,
                LocationServiceDay.service_date,
                LocationServiceDay.is_open,
                LocationServiceDay.closed_reason,
                LocationServiceDay.capacity,
                cast(booked, Integer).label("booked"),
                func.greatest(held - cast(booked, Integer), 0).label("awaiting_payment"),
                func.public.service_day_places_left(LocationServiceDay.id).label("places_left"),
                ever_booked.label("ever_booked"),
                (LocationServiceDay.service_date < location_today).label("is_past"),
            )
            .join(Location, Location.id == LocationServiceDay.location_id)
            .filter(
                LocationServiceDay.location_service_id == location_service_id,
                LocationServiceDay.service_date >= date_from,
                LocationServiceDay.service_date <= date_to,
            )
            .order_by(LocationServiceDay.service_date)
            .all()
        )

    def create_many(
        self,
        *,
        location_service_id: UUID,
        location_id: UUID,
        dates: list[date],
        capacity: int,
    ) -> list[date]:
        """Adds these days; ones that already exist are left alone. Returns the dates added."""
        if not dates:
            return []

        rows = self.db.execute(
            text("""
                INSERT INTO public.location_service_days (location_service_id, location_id, service_date, capacity)
                SELECT :location_service_id, :location_id, day, :capacity
                FROM unnest(CAST(:dates AS date[])) AS day
                ON CONFLICT (location_service_id, service_date) DO NOTHING
                RETURNING service_date
            """),
            {
                "location_service_id": location_service_id,
                "location_id": location_id,
                "dates": dates,
                "capacity": capacity,
            },
        ).all()

        return sorted(row.service_date for row in rows)

    def places_held(
        self,
        *,
        id: UUID,
    ) -> int:
        return self.db.execute(
            text("SELECT public.service_day_places_held(:id)"),
            {"id": id},
        ).scalar_one()

    def update(
        self,
        *,
        day: LocationServiceDay,
        values: dict,
    ) -> LocationServiceDay:
        for field, value in values.items():
            setattr(day, field, value)

        self.db.flush()
        self.db.refresh(day)

        return day

    def held_above(
        self,
        *,
        location_service_id: UUID,
        date_from: date,
        date_to: date,
        capacity: int,
    ) -> list[Row]:
        """The range's days whose bookings hold more places than `capacity`."""
        held = func.public.service_day_places_held(LocationServiceDay.id)

        return (
            self.db.query(LocationServiceDay.service_date, held.label("held"))
            .filter(
                LocationServiceDay.location_service_id == location_service_id,
                LocationServiceDay.service_date >= date_from,
                LocationServiceDay.service_date <= date_to,
                held > capacity,
            )
            .order_by(LocationServiceDay.service_date)
            .all()
        )

    def set_capacity(
        self,
        *,
        location_service_id: UUID,
        date_from: date,
        date_to: date,
        capacity: int,
    ) -> int:
        result = self.db.execute(
            text("""
                UPDATE public.location_service_days
                SET capacity = :capacity
                WHERE location_service_id = :location_service_id
                  AND service_date BETWEEN :date_from AND :date_to
            """),
            {
                "location_service_id": location_service_id,
                "date_from": date_from,
                "date_to": date_to,
                "capacity": capacity,
            },
        )

        return result.rowcount

    def delete(
        self,
        *,
        day: LocationServiceDay,
    ) -> None:
        self.db.delete(day)
        self.db.flush()
