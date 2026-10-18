from uuid import UUID
from datetime import date, datetime

from sqlalchemy import String, case, cast, distinct, func, tuple_, update
from sqlalchemy.engine import Row

from app.db.repository import Pagination, Repository
from app.db.models import (
    Booking,
    BookingGroup,
    ChildProfile,
    LocationService,
    LocationServiceDay,
    ServiceType,
)
from app.public.schemas.enums import BookingStatus, PaymentStatus


def _child_name():
    return func.concat(
        ChildProfile.first_name,
        " ",
        ChildProfile.last_name,
    ).label("child_name")


def _effective_status():
    """
    The booking status to show and filter on: a PENDING hold that has
    lapsed reads as EXPIRED (public.effective_booking_status, schema/0009).
    Writes use the raw Booking.booking_status.
    """
    return func.public.effective_booking_status(
        Booking.booking_status,
        Booking.created_at,
        type_=Booking.__table__.c.booking_status.type,
    )


class BookingRepository(Repository):
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
        booking_status: BookingStatus = BookingStatus.PENDING,
        payment_status: PaymentStatus = PaymentStatus.PENDING,
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
                _child_name(),
                Booking.location_service_day_id,
                LocationServiceDay.service_date.label(
                    "location_service_date"
                ),
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
                _effective_status().in_(
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

    def get_group_statuses(
        self,
        *,
        booking_group_id: UUID,
    ) -> set[BookingStatus]:
        """The group's effective statuses (empty if RLS hides the group)."""
        rows = (
            self.db.query(_effective_status())
            .filter(Booking.booking_group_id == booking_group_id)
            .distinct()
            .all()
        )

        return {row[0] for row in rows}

    def list_group_summaries(
        self,
        *,
        pagination: Pagination | None = None,
    ) -> list[Row]:
        """
        One row per booking group (a checkout), upcoming first: groups
        still running or ahead by their first day (soonest first), then past
        groups (most recent first).
        """
        first_date = func.min(LocationServiceDay.service_date)
        last_date = func.max(LocationServiceDay.service_date)
        is_past = last_date < func.current_date()

        query = (
            self.db.query(
                BookingGroup.id.label("booking_group_id"),
                BookingGroup.created_at,
                func.min(ServiceType.name).label("service_name"),
                func.array_agg(
                    distinct(_child_name().element)
                ).label("child_names"),
                # Cast to text: psycopg2 can't parse arrays of our enum types.
                func.array_agg(
                    distinct(cast(_effective_status(), String))
                ).label("statuses"),
                first_date.label("first_date"),
                last_date.label("last_date"),
                func.count(Booking.id).label("booking_count"),
                func.sum(Booking.price_snapshot_cents).label("total_cents"),
                func.min(cast(Booking.currency, String)).label("currency"),
            )
            .join(
                Booking,
                Booking.booking_group_id == BookingGroup.id,
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
            .group_by(
                BookingGroup.id,
                BookingGroup.created_at,
            )
            .order_by(
                case((is_past, 1), else_=0).asc(),
                case((~is_past, first_date)).asc(),
                first_date.desc(),
                BookingGroup.created_at.desc(),
            )
        )

        return self._all(query, pagination)

    def settle_pending_for_group(
        self,
        *,
        booking_group_id: UUID,
        booking_status: BookingStatus,
        payment_status: PaymentStatus,
        cancelled_at: datetime | None = None,
    ) -> int:
        """
        Move the group's still-PENDING bookings to a final status. Bookings
        already settled are left alone, so repeat webhooks are no-ops.
        """
        values = {
            "booking_status": booking_status,
            "payment_status": payment_status,
        }

        if cancelled_at is not None:
            values["cancelled_at"] = cancelled_at

        result = self.db.execute(
            update(Booking)
            .where(
                Booking.booking_group_id == booking_group_id,
                Booking.booking_status == BookingStatus.PENDING,
            )
            .values(**values)
        )

        return result.rowcount

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
                _child_name(),
                LocationServiceDay.service_date,
                ServiceType.name.label("service_name"),
                _effective_status().label("booking_status"),
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
        booking_group_id: UUID | None = None,
        pagination: Pagination | None = None,
    ) -> list[Row]:
        effective_status = _effective_status()

        query = (
            self.db.query(
                Booking.id,
                Booking.location_id,
                Booking.user_id,
                Booking.booking_group_id,
                Booking.location_service_day_id,
                Booking.child_id,
                _child_name(),
                LocationServiceDay.service_date,
                ServiceType.name.label("service_name"),
                effective_status.label("booking_status"),
                Booking.payment_status,
                Booking.price_snapshot_cents,
                Booking.currency,
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
                effective_status.in_(booking_status)
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

        if booking_group_id:
            query = query.filter(
                Booking.booking_group_id == booking_group_id
            )

        return self._all(
            query.order_by(
                LocationServiceDay.service_date.asc(),
                ChildProfile.first_name.asc(),
            ),
            pagination,
        )
