import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repository import Pagination
from app.errors.bookings import (
    BookingGroupNotFoundError,
    BookingNotFoundError,
    CheckoutNotFoundError,
)
from app.errors.payments import PaymentProviderError
from app.integrations.payments.stripe.settlement import confirm_with_stripe
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.schemas.booking import (
    FamilyBookingResponse,
    BookingGroupLineResponse,
    BookingGroupResponse,
    BookingGroupSummaryResponse,
    ListBookingGroupsFilterRequest,
    BookingResponse,
    BookingTableResponse,
    CheckoutStatusResponse,
    ListBookingsFilterRequest
)
from app.public.schemas.enums import BookingStatus, StripeStatus
from app.public.services.attendance import location_today
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.payments")


# A group's bookings are settled together, but a group can still mix
# statuses (e.g. one lapsed hold swept by the trigger). The group is as
# "live" as its liveliest booking.
_GROUP_STATUS_PRIORITY = (
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.EXPIRED,
    BookingStatus.CANCELLED,
)


def resolve_group_status(
    statuses: set[BookingStatus],
) -> BookingStatus | None:
    """The group's overall status from its bookings' effective statuses."""
    for status in _GROUP_STATUS_PRIORITY:
        if status in statuses:
            return status

    return None


class ReadBookingService:
    def __init__(
        self,
        *,
        db: Session,
        booking_repository: BookingRepository,
        payment_attempt_repository: PaymentAttemptRepository,
    ):
        self.db = db
        self.booking_repository = booking_repository
        self.payment_attempt_repository = payment_attempt_repository

    def list_groups(
        self,
        *,
        filters: ListBookingGroupsFilterRequest,
    ) -> list[BookingGroupSummaryResponse]:
        rows = self.booking_repository.list_group_summaries(
            scope=filters.scope,
            pagination=filters,
        )

        return [
            BookingGroupSummaryResponse(
                booking_group_id=row.booking_group_id,
                created_at=row.created_at,
                status=resolve_group_status(
                    {BookingStatus(status) for status in row.statuses}
                ),
                paid_at=row.paid_at,
                service_name=row.service_name,
                child_names=sorted(row.child_names),
                first_date=row.first_date,
                last_date=row.last_date,
                booking_count=row.booking_count,
                total_cents=row.total_cents,
                currency=row.currency,
            )
            for row in rows
        ]

    def get_group(
        self,
        *,
        booking_group_id: UUID,
    ) -> BookingGroupResponse:
        rows = self.booking_repository.list_context_with_filters(
            booking_group_id=booking_group_id,
        )

        if not rows:
            raise BookingGroupNotFoundError()

        bookings = [
            BookingGroupLineResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]

        payment = self.payment_attempt_repository.get_successful_by_booking_group_id(
            booking_group_id=booking_group_id,
        )

        return BookingGroupResponse(
            booking_group_id=booking_group_id,
            status=resolve_group_status(
                {booking.booking_status for booking in bookings}
            ),
            paid_at=payment.paid_at if payment else None,
            receipt_url=payment.stripe_receipt_url if payment else None,
            total_cents=sum(
                booking.price_snapshot_cents
                for booking in bookings
            ),
            currency=bookings[0].currency,
            bookings=bookings,
        )

    def get_checkout_status(
        self,
        *,
        checkout_session_id: str,
    ) -> CheckoutStatusResponse:
        """
        What the success page shows after Stripe's redirect. A pending
        payment is checked with Stripe first and settled if it's been paid,
        so a missed webhook doesn't leave the family stuck on "awaiting
        payment". If Stripe can't be reached it shows what we know.
        """
        attempt = self.payment_attempt_repository.get_by_checkout_session_id(
            checkout_session_id=checkout_session_id,
        )

        if not attempt:
            raise CheckoutNotFoundError()

        if attempt.stripe_status == StripeStatus.PENDING:
            try:
                confirm_with_stripe(attempt)
            except PaymentProviderError as exc:
                logger.warning(
                    "Couldn't check the payment with Stripe",
                    extra={
                        "event": "stripe_payment_check_unavailable",
                        "result": "skipped",
                        "reason": f"payment_attempt_id={attempt.id}; {exc.log_reason}",
                    },
                )

            # Settled on its own session; read what it decided.
            self.db.refresh(attempt)

        rows = self.booking_repository.list_context_with_filters(
            booking_group_id=attempt.booking_group_id,
        )

        return CheckoutStatusResponse(
            booking_group_id=attempt.booking_group_id,
            payment_status=attempt.stripe_status,
            total_cents=attempt.total_cents,
            currency=attempt.currency,
            bookings=[
                BookingTableResponse.model_validate(
                    row,
                    from_attributes=True,
                )
                for row in rows
            ],
        )

    def get_by_id(
        self,
        *,
        id: UUID
    ) -> BookingResponse:
        row = self.booking_repository.get_with_context_by_id(
            id=id
        )

        if not row:
            raise BookingNotFoundError()

        return BookingResponse.model_validate(
            row,
            from_attributes=True,
        )

    def list_with_filters(
        self,
        *,
        filters: ListBookingsFilterRequest,
        pagination: Pagination,
    ) -> list[BookingTableResponse]:
        rows = self.booking_repository.list_context_with_filters(
            booking_status=filters.booking_status,
            payment_status=filters.payment_status,
            date_from=filters.date_from,
            date_to=filters.date_to,
            pagination=pagination,
        )

        return [
            BookingTableResponse.model_validate(
                row,
                from_attributes=True,
            )
            for row in rows
        ]


# How far ahead staff see a family's bookings (plus anything unpaid).
FAMILY_BOOKINGS_DAYS = 14


class ReadFamilyBookingsService:
    """
    A family's bookings for staff at the staff kiosk: today to 2 weeks
    ahead, and anything still awaiting payment. Read-only; refunds are the
    admins' (CreateRefundService).
    """

    def __init__(
        self,
        *,
        db: Session,
        booking_repository: BookingRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.booking_repository = booking_repository
        self.location_repository = location_repository

    def list(
        self,
        *,
        location_id: UUID,
        family_user_id: UUID,
    ) -> list[FamilyBookingResponse]:
        today = location_today(self.location_repository.get_by_id(id=location_id))
        rows = self.booking_repository.list_family_for_staff(
            user_id=family_user_id,
            date_from=today,
            date_to=today + timedelta(days=FAMILY_BOOKINGS_DAYS),
        )

        return [FamilyBookingResponse.model_validate(row, from_attributes=True) for row in rows]
