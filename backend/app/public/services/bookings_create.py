from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.auth.jwt.context import TokenContext
from app.integrations.payments.stripe.client import StripeClient
from app.errors.bookings import (
    BookingCollisionError,
    MultipleBookingServicesError,
    BookingGroupAlreadyPaidError,
    BookingCapacityCollisionError,
    InvalidBookingServiceDaysError,
)
from app.public.schemas.booking import (
    CreateBookingRequest,
    CreateBookingResponse,
    BookingConflictRow,
)
from app.public.models.booking import Booking
from app.public.models.booking_group import BookingGroup
from app.public.repositories.booking_group import BookingGroupRepository
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.repositories.location_service import LocationServiceRepository


@dataclass
class PendingBookingGroup:
    booking_group: BookingGroup
    bookings: list[Booking]
    amount: int


@dataclass
class ResolvedBookingPrice:
    price_cents: int
    currency: str


class CreateBookingService:
    def __init__(self, *, db: Session, ctx: TokenContext):
        self.db = db
        self.ctx = ctx

        self.booking_group_repository = BookingGroupRepository(db=db)
        self.booking_repository = BookingRepository(db=db)
        self.payment_attempt_repository = PaymentAttemptRepository(db=db)
        self.location_service_repository = LocationServiceRepository(db=db)

        self.stripe = StripeClient()

    def create(
        self,
        *,
        body: CreateBookingRequest,
    ) -> CreateBookingResponse:
        try:
            # Resolve and lock requested service days
            resolved_service_days = self._resolve_service_days(
                body=body,
            )

            # Resume existing booking group
            pending_booking_group = self._resolve_pending_booking(
                idempotency_key=body.idempotency_key,
            )

            if pending_booking_group:
                return CreateBookingResponse(
                    idempotency_key=(
                        pending_booking_group.booking_group.idempotency_key
                    ),
                    booking_group_id=pending_booking_group.booking_group.id,
                    amount=pending_booking_group.amount,
                )

            # Validate booking availability
            self._validate_capacity(
                body=body,
                resolved_service_days=resolved_service_days,
            )

            booking_conflicts = self.find_conflicts(
                body=body,
            )

            if booking_conflicts:
                raise BookingCollisionError(
                    conflicts=booking_conflicts,
                )

            # Resolve price only after local validation succeeds
            pricing = self._resolve_booking_price(
                resolved_service_day=resolved_service_days[0],
            )

            # Create booking group
            booking_group = self.booking_group_repository.create(
                idempotency_key=body.idempotency_key,
                user_id=self.ctx.user_id,
                source=None,
            )

            # Create bookings
            bookings: list[Booking] = []

            for selection in body.bookings:
                for location_service_day_id in selection.location_service_days:
                    bookings.append(
                        self.booking_repository.create(
                            location_id=self.ctx.location_id,
                            user_id=self.ctx.user_id,
                            booking_group_id=booking_group.id,
                            location_service_day_id=location_service_day_id,
                            child_id=selection.child_id,
                            price_snapshot_cents=pricing.price_cents,
                            currency=pricing.currency,
                            booking_status="PENDING",
                        )
                    )

            self.db.commit()

            return CreateBookingResponse(
                idempotency_key=booking_group.idempotency_key,
                booking_group_id=booking_group.id,
                amount=sum(
                    booking.price_snapshot_cents
                    for booking in bookings
                ),
            )

        except Exception:
            self.db.rollback()
            raise

    def find_conflicts(
        self,
        *,
        body: CreateBookingRequest,
    ) -> list[BookingConflictRow]:
        requested_pairs = [
            (
                selection.child_id,
                location_service_day_id,
            )
            for selection in body.bookings
            for location_service_day_id in selection.location_service_days
        ]

        conflicts = self.booking_repository.find_conflicts(
            pairs=requested_pairs,
        )

        return [
            BookingConflictRow(
                child_id=conflict.child_id,
                child_name=f"{conflict.first_name} {conflict.last_name}",
                location_service_day_id=conflict.location_service_day_id,
                service_date=conflict.service_date,
            )
            for conflict in conflicts
        ]

    def _resolve_pending_booking(
        self,
        *,
        idempotency_key: str,
    ) -> PendingBookingGroup | None:
        existing_booking_group = (
            self.booking_group_repository.get_pending_by_idempotency_key(
                idempotency_key=idempotency_key,
            )
        )

        if not existing_booking_group:
            return None

        successful_payment_attempt = (
            self.payment_attempt_repository.get_successful_by_booking_group_id(
                booking_group_id=existing_booking_group.id,
            )
        )

        if successful_payment_attempt:
            raise BookingGroupAlreadyPaidError()

        bookings = (
            self.booking_repository.list_by_booking_group_id(
                booking_group_id=existing_booking_group.id,
            )
        )

        return PendingBookingGroup(
            booking_group=existing_booking_group,
            bookings=bookings,
            amount=sum(
                booking.price_snapshot_cents
                for booking in bookings
            ),
        )

    def _resolve_booking_price(
        self,
        *,
        resolved_service_day,
    ) -> ResolvedBookingPrice:
        stripe_price = self.stripe.get_price(
            stripe_price_id=resolved_service_day.stripe_price_id,
        )

        return ResolvedBookingPrice(
            price_cents=stripe_price.amount_cents,
            currency=stripe_price.currency,
        )

    def _validate_capacity(
        self,
        *,
        body: CreateBookingRequest,
        resolved_service_days,
    ) -> None:
        requested_counts = Counter(
            location_service_day_id
            for selection in body.bookings
            for location_service_day_id in selection.location_service_days
        )

        capacity_conflicts = []

        for resolved_service_day in resolved_service_days:
            active_booking_count = (
                self.booking_repository.count_active_for_service_day(
                    location_service_day_id=(
                        resolved_service_day.location_service_day_id
                    ),
                )
            )

            requested_booking_count = requested_counts[
                resolved_service_day.location_service_day_id
            ]

            if (
                active_booking_count + requested_booking_count
                > resolved_service_day.capacity
            ):
                capacity_conflicts.append(
                    resolved_service_day.service_date
                )

        if capacity_conflicts:
            raise BookingCapacityCollisionError(
                service_dates=capacity_conflicts,
            )

    def _resolve_service_days(
        self,
        *,
        body: CreateBookingRequest,
    ):
        service_day_ids = [
            location_service_day_id
            for selection in body.bookings
            for location_service_day_id in selection.location_service_days
        ]

        resolved_service_days = (
            self.location_service_repository.list_by_service_day_ids(
                ids=service_day_ids,
            )
        )

        requested_service_day_ids = set(
            service_day_ids
        )

        resolved_service_day_ids = {
            resolved_service_day.location_service_day_id
            for resolved_service_day in resolved_service_days
        }

        if requested_service_day_ids != resolved_service_day_ids:
            raise InvalidBookingServiceDaysError()

        location_service_ids = {
            resolved_service_day.location_service_id
            for resolved_service_day in resolved_service_days
        }

        if len(location_service_ids) != 1:
            raise MultipleBookingServicesError()

        return resolved_service_days