from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.bookings import (
    BookingAttemptFinishedError,
    BookingGroupAlreadyPaidError,
    BookingGroupNotFoundError,
)
from app.integrations.payments.stripe.client import StripeClient
from app.public.repositories.booking import BookingRepository
from app.public.repositories.booking_group import BookingGroupRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.schemas.enums import BookingStatus, PaymentStatus, StripeStatus
from app.public.services.bookings_read import resolve_group_status


class UpdateBookingService:
    def __init__(
        self,
        *,
        db: Session,
        booking_group_repository: BookingGroupRepository,
        booking_repository: BookingRepository,
        payment_attempt_repository: PaymentAttemptRepository,
    ):
        self.db = db
        self.booking_group_repository = booking_group_repository
        self.booking_repository = booking_repository
        self.payment_attempt_repository = payment_attempt_repository
        self.stripe = StripeClient()

    @transactional
    def cancel_group(
        self,
        *,
        booking_group_id: UUID,
    ) -> None:
        """
        Cancel a pending group and release its places.

        The Stripe session is closed first: otherwise a checkout left open
        in another tab could still be paid, and the webhook would take the
        money for bookings that no longer exist.
        """
        booking_group = self.booking_group_repository.get_by_id(
            id=booking_group_id,
        )

        if not booking_group:
            raise BookingGroupNotFoundError()

        status = resolve_group_status(
            self.booking_repository.get_group_statuses(
                booking_group_id=booking_group.id,
            )
        )

        if status == BookingStatus.CONFIRMED:
            raise BookingGroupAlreadyPaidError()

        if status != BookingStatus.PENDING:
            raise BookingAttemptFinishedError()

        attempt = self.payment_attempt_repository.get_latest_by_booking_group_id(
            booking_group_id=booking_group.id,
        )

        if attempt and attempt.stripe_checkout_session_id:
            checkout = self.stripe.get_checkout_session(
                checkout_session_id=attempt.stripe_checkout_session_id,
            )

            # Paid, but the webhook hasn't landed yet: it will confirm them.
            if checkout.status == "complete":
                raise BookingGroupAlreadyPaidError()

            if checkout.status == "open":
                self.stripe.expire_checkout_session(
                    checkout_session_id=attempt.stripe_checkout_session_id,
                )

        if attempt and attempt.stripe_status == StripeStatus.PENDING:
            attempt.stripe_status = StripeStatus.FAILED

        self.booking_repository.settle_pending_for_group(
            booking_group_id=booking_group.id,
            booking_status=BookingStatus.CANCELLED,
            payment_status=PaymentStatus.FAILED,
            cancelled_at=datetime.now(timezone.utc),
        )
