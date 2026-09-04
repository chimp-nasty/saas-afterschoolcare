from uuid import UUID
from datetime import date

from sqlalchemy import tuple_
from sqlalchemy.orm import Session
from sqlalchemy.engine import Row

from app.public.models.booking import Booking
from app.public.models.child_profile import ChildProfile
from app.public.models.location_service_day import LocationServiceDay
from app.public.models.location_service import LocationService
from app.public.models.service_type import ServiceType


class BookingRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        booking_group_id: UUID,
        location_service_day_id: UUID,
        child_id: UUID,
        price_snapshot_cents: int,
        currency: str,
        booking_status: str = "PENDING",
        payment_status: str = "PENDING",
        cancelled_at=None,
    ) -> Booking:
        record = Booking(
            location_id=location_id,
            user_id=user_id,
            booking_group_id=booking_group_id,
            location_service_day_id=location_service_day_id,
            child_id=child_id,
            booking_status=booking_status,
            payment_status=payment_status,
            cancelled_at=cancelled_at,
            price_snapshot_cents=price_snapshot_cents,
            currency=currency,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Booking | None:
        return (
            self.db.query(Booking)
            .filter(Booking.id == id)
            .first()
        )

    def find_conflicts(
        self,
        *,
        pairs: list[tuple[UUID, UUID]],
    ) -> list[Row]:
        if not pairs:
            return []

        return (
            self.db.query(
                Booking.child_id,
                ChildProfile.first_name,
                ChildProfile.last_name,
                Booking.location_service_day_id.label(
                    "location_service_day_id"
                ),
                LocationServiceDay.service_date,
            )
            .join(
                ChildProfile,
                ChildProfile.id == Booking.child_id,
            )
            .join(
                LocationServiceDay,
                LocationServiceDay.id == Booking.location_service_day_id,
            )
            .filter(
                Booking.booking_status.in_(
                    ["PENDING", "CONFIRMED"]
                ),
                tuple_(
                    Booking.child_id,
                    Booking.location_service_day_id,
                ).in_(pairs),
            )
            .all()
        )

    def list_by_booking_group_id(
        self,
        *,
        booking_group_id: UUID
    ) -> list[Booking]:
        return (
            self.db.query(Booking)
            .filter(Booking.booking_group_id == booking_group_id)
            .all()
        )

    def count_active_for_service_day(
        self,
        *,
        location_service_day_id: UUID,
    ) -> int:
        return (
            self.db.query(Booking)
            .filter(
                Booking.location_service_day_id == location_service_day_id,
                Booking.booking_status.in_(
                    ["PENDING", "CONFIRMED"]
                ),
            )
            .count()
        )

    def get_with_context_by_id(
        self,
        *,
        id: UUID,
    ) -> Row | None:
        return (
            self.db.query(
                Booking.id,
                Booking.location_id,
                Booking.user_id,
                Booking.booking_group_id,
                Booking.location_service_day_id,
                Booking.child_id,

                ChildProfile.first_name,
                ChildProfile.last_name,

                LocationServiceDay.service_date,
                ServiceType.name.label("service_name"),

                Booking.booking_status,
                Booking.payment_status,
                Booking.cancelled_at,
                Booking.price_snapshot_cents,
                Booking.currency,
                Booking.created_at,
                Booking.updated_at,
            )
            .join(
                ChildProfile,
                ChildProfile.id == Booking.child_id,
            )
            .join(
                LocationServiceDay,
                LocationServiceDay.id == Booking.location_service_day_id,
            )
            .join(
                LocationService,
                LocationService.id == LocationServiceDay.location_service_id,
            )
            .join(
                ServiceType,
                ServiceType.id == LocationService.service_type_id,
            )
            .filter(
                Booking.id == id,
            )
            .first()
        )

    def list_context_with_filters(
        self,
        *,
        booking_status: list[str] | None = None,
        payment_status: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Row]:
        query = (
            self.db.query(
                Booking.id,
                Booking.location_id,
                Booking.user_id,
                Booking.booking_group_id,
                Booking.location_service_day_id,
                Booking.child_id,

                ChildProfile.first_name,
                ChildProfile.last_name,

                LocationServiceDay.service_date,
                ServiceType.name.label("service_name"),

                Booking.booking_status,
                Booking.payment_status,
            )
            .join(
                ChildProfile,
                ChildProfile.id == Booking.child_id,
            )
            .join(
                LocationServiceDay,
                LocationServiceDay.id == Booking.location_service_day_id,
            )
            .join(
                LocationService,
                LocationService.id == LocationServiceDay.location_service_id,
            )
            .join(
                ServiceType,
                ServiceType.id == LocationService.service_type_id,
            )
        )

        if booking_status:
            query = query.filter(
                Booking.booking_status.in_(booking_status)
            )

        if payment_status:
            query = query.filter(
                Booking.payment_status.in_(payment_status)
            )

        if date_from:
            query = query.filter(
                LocationServiceDay.service_date >= date_from
            )

        if date_to:
            query = query.filter(
                LocationServiceDay.service_date <= date_to
            )

        return (
            query
            .order_by(
                LocationServiceDay.service_date.asc()
            )
            .all()
        )