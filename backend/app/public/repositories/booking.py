from uuid import UUID
from datetime import date, datetime

from sqlalchemy import Date, String, and_, case, cast, distinct, func, or_, select, tuple_, update
from sqlalchemy.engine import Row

from app.db.repository import Pagination, Repository
from app.db.models import (
    Booking,
    BookingGroup,
    Refund,
    ChildProfile,
    Location,
    LocationService,
    LocationServiceConfig,
    LocationServiceDay,
    PaymentAttempt,
    ServiceType,
)
from app.public.schemas.enums import (
    BookingGroupScope,
    BookingStatus,
    PaymentStatus,
    StripeStatus,
)


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


def _location_today():
    """Today's date where the location is. Needs Location joined."""
    return cast(func.timezone(Location.timezone, func.now()), Date)


def _refundable_until():
    """
    The last day (location time) the family can refund a booking,
    inclusive: refund_cutoff_days before its session (schema/0004). Needs
    LocationServiceDay and LocationServiceConfig joined.
    """
    return LocationServiceDay.service_date - LocationServiceConfig.refund_cutoff_days


def _session_times():
    """
    A booking's session times. Every screen reads them through here, so
    per-day overrides (an early finish) can be added in this one place
    later. Needs LocationServiceConfig joined.
    """
    return (
        LocationServiceConfig.start_time.label("start_time"),
        LocationServiceConfig.end_time.label("end_time"),
    )


def _is_refundable_by_family():
    """
    Whether the family can refund the booking now. The rule lives in the
    database (public.booking_is_refundable, schema/0004), where the refund
    trigger uses it too.
    """
    return func.public.booking_is_refundable(Booking.id, False)


def _is_refundable_by_admin():
    """Whether an admin can refund it now: up to and including its day."""
    return func.public.booking_is_refundable(Booking.id, True)


def _is_cancellable():
    """
    Whether it can be cancelled without a refund now: once the family's
    refund window has closed, until the session starts. The rule lives in
    the database (public.booking_is_cancellable, schema/0004), where the
    booking trigger uses it too; the same for families and admins.
    """
    return func.public.booking_is_cancellable(Booking.id)


def _is_reinstatable():
    """Whether a booking cancelled without a refund can be put back (until its session starts)."""
    return func.public.booking_is_reinstatable(Booking.id)


def _latest_refund_status():
    return (
        select(Refund.status)
        .where(Refund.booking_id == Booking.id)
        .order_by(Refund.created_at.desc())
        .limit(1)
        .correlate(Booking)
        .scalar_subquery()
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

    def has_upcoming_for_child(
        self,
        *,
        child_id: UUID,
    ) -> bool:
        """
        Whether the child has a pending or confirmed booking from today on
        (location time). A lapsed hold doesn't count.
        """
        return self.db.query(
            self.db.query(Booking)
            .join(
                LocationServiceDay,
                LocationServiceDay.id == Booking.location_service_day_id,
            )
            .join(
                Location,
                Location.id == Booking.location_id,
            )
            .filter(
                Booking.child_id == child_id,
                _effective_status().in_(["PENDING", "CONFIRMED"]),
                LocationServiceDay.service_date >= _location_today(),
            )
            .exists()
        ).scalar()

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
        scope: BookingGroupScope | None = None,
        pagination: Pagination | None = None,
    ) -> list[Row]:
        """
        One row per booking group (a checkout), upcoming first: groups
        still running or ahead by their first day (soonest first), then past
        groups (most recent first).
        """
        first_date = func.min(LocationServiceDay.service_date)
        last_date = func.max(LocationServiceDay.service_date)

        # "Today" where the location is, not where the database is.
        is_past = last_date < _location_today()

        # Same rule as resolve_group_status: the group is live if any of
        # its bookings is.
        is_live = func.bool_or(
            _effective_status().in_(["PENDING", "CONFIRMED"])
        )

        # A subquery, not a join: joining attempts would repeat each
        # booking row once per attempt and inflate the counts and totals.
        paid_at = (
            self.db.query(func.max(PaymentAttempt.paid_at))
            .filter(
                PaymentAttempt.booking_group_id == BookingGroup.id,
                PaymentAttempt.stripe_status == StripeStatus.SUCCEEDED,
            )
            .correlate(BookingGroup)
            .scalar_subquery()
        )

        query = (
            self.db.query(
                BookingGroup.id.label("booking_group_id"),
                BookingGroup.created_at,
                paid_at.label("paid_at"),
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
            .join(
                Location,
                Location.id == BookingGroup.location_id,
            )
            .group_by(
                BookingGroup.id,
                BookingGroup.created_at,
                Location.timezone,
            )
            .order_by(
                case((is_past, 1), else_=0).asc(),
                case((~is_past, first_date)).asc(),
                first_date.desc(),
                BookingGroup.created_at.desc(),
            )
        )

        if scope == BookingGroupScope.UPCOMING:
            query = query.having(and_(~is_past, is_live))
        elif scope == BookingGroupScope.HISTORY:
            query = query.having(or_(is_past, ~is_live))

        return self._all(query, pagination)

    def mark_refunded(
        self,
        *,
        booking_id: UUID,
    ) -> int:
        """
        A refund went through: cancel the booking (releasing its place).
        Only a confirmed, paid booking moves, so repeat webhooks are no-ops.
        """
        result = self.db.execute(
            update(Booking)
            .where(
                Booking.id == booking_id,
                Booking.booking_status == BookingStatus.CONFIRMED,
                Booking.payment_status == PaymentStatus.PAID,
            )
            .values(
                booking_status=BookingStatus.CANCELLED,
                payment_status=PaymentStatus.REFUNDED,
                cancelled_at=func.now(),
            )
        )

        return result.rowcount

    def set_paid_status(
        self,
        *,
        booking_id: UUID,
        from_status: BookingStatus,
        to_status: BookingStatus,
    ) -> int:
        """
        Cancel a paid booking without a refund (CONFIRMED -> CANCELLED), or
        reinstate it (CANCELLED -> CONFIRMED); RLS: the family's own, or the
        location's for admins. Only a paid booking in from_status moves (0
        rows otherwise). Whether it may now, and when it was cancelled, are
        the database's (trg_bookings_cancel_rules; a reinstated booking
        passes the booking rules again).
        """
        result = self.db.execute(
            update(Booking)
            .where(
                Booking.id == booking_id,
                Booking.booking_status == from_status,
                Booking.payment_status == PaymentStatus.PAID,
            )
            .values(booking_status=to_status)
        )

        return result.rowcount

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

    def list_family_for_staff(
        self,
        *,
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[Row]:
        """
        A family's bookings for staff (RLS: the location's): those between
        the dates, and any still awaiting payment, whatever the date.
        """
        effective_status = _effective_status()

        query = (
            self._context_query(effective_status)
            .add_columns(_is_refundable_by_admin().label("is_refundable_by_admin"))
            .filter(
                Booking.user_id == user_id,
                or_(
                    and_(
                        LocationServiceDay.service_date >= date_from,
                        LocationServiceDay.service_date <= date_to,
                    ),
                    effective_status == "PENDING",
                ),
            )
        )

        return query.order_by(
            LocationServiceDay.service_date.asc(),
            ChildProfile.first_name.asc(),
        ).all()

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
        query = self._context_query(effective_status)

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

    def _context_query(self, effective_status):
        """Bookings with their child, session and refund details (RLS applies)."""
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
                effective_status.label("booking_status"),
                Booking.payment_status,
                Booking.price_snapshot_cents,
                Booking.currency,
                *_session_times(),
                _refundable_until().label("refundable_until"),
                _is_refundable_by_family().label("is_refundable"),
                _is_cancellable().label("is_cancellable"),
                _is_reinstatable().label("is_reinstatable"),
                _latest_refund_status().label("refund_status"),
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
            .join(
                LocationServiceConfig,
                LocationServiceConfig.location_service_id == LocationService.id,
            )
            .join(
                Location,
                Location.id == Booking.location_id,
            )
        )
