from uuid import UUID
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.transaction import transactional
from app.errors.bookings import (
    BookingAttemptFinishedError,
    BookingGroupNotFoundError,
    CheckoutOriginError,
    MultipleBookingServicesError,
    BookingGroupAlreadyPaidError,
    InvalidBookingServiceDaysError,
)
from app.integrations.payments.stripe.client import (
    CheckoutLineItem,
    StripeCheckout,
    StripeClient,
)
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.repositories.tenant import TenantRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.errors.customer import CustomerProfileIncompleteError
from app.public.schemas.booking import (
    CreateBookingRequest,
    CreateBookingResponse,
    BookingConflictRow,
    CheckoutUrlResponse,
)
from app.public.schemas.enums import BookingStatus
from app.public.services.bookings_read import resolve_group_status
from app.db.models import Booking, BookingGroup
from app.public.repositories.booking_group import BookingGroupRepository
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.repositories.location_service_day import LocationServiceDayRepository


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
    def __init__(
        self,
        *,
        db: Session,
        booking_group_repository: BookingGroupRepository,
        booking_repository: BookingRepository,
        payment_attempt_repository: PaymentAttemptRepository,
        location_service_repository: LocationServiceDayRepository,
        location_repository: LocationRepository,
        tenant_repository: TenantRepository,
        customer_profile_repository: CustomerProfileRepository,
    ):
        self.db = db

        self.booking_group_repository = booking_group_repository
        self.booking_repository = booking_repository
        self.payment_attempt_repository = payment_attempt_repository
        self.location_service_repository = location_service_repository
        self.location_repository = location_repository
        self.tenant_repository = tenant_repository
        self.customer_profile_repository = customer_profile_repository
        self.stripe = StripeClient()

    @transactional
    def create(
        self,
        *,
        body: CreateBookingRequest,
        user_id: UUID,
        location_id: UUID,
        origin: str | None,
    ) -> CreateBookingResponse:
        self._require_complete_profile(user_id=user_id)

        site_url = self._site_url(
            location_id=location_id,
            origin=origin,
        )

        # Resolve and lock requested service days
        resolved_service_days = self._resolve_service_days(
            body=body,
        )

        # Resume existing booking group
        pending_booking_group = self._resolve_pending_booking(
            idempotency_key=body.idempotency_key,
        )

        if pending_booking_group:
            checkout = self._resume_checkout(
                pending=pending_booking_group,
                resolved_service_days=resolved_service_days,
                site_url=site_url,
            )

            return CreateBookingResponse(
                idempotency_key=(
                    pending_booking_group.booking_group.idempotency_key
                ),
                booking_group_id=pending_booking_group.booking_group.id,
                amount=pending_booking_group.amount,
                checkout_url=checkout.checkout_url,
            )

        # Everything else is enforced by the database and mapped to API
        # errors in app/errors/database.py: duplicates, children or days
        # that aren't this user's/location's, and (trigger, schema/0008)
        # past or closed days, full days and children awaiting review.

        pricing = resolved_service_days[0]

        # Create booking group
        booking_group = self.booking_group_repository.create(
            idempotency_key=body.idempotency_key,
            user_id=user_id,
            location_id=location_id,
            source=None,
        )

        # Create bookings
        bookings: list[Booking] = []

        for selection in body.bookings:
            for location_service_day_id in selection.location_service_days:
                bookings.append(
                    self.booking_repository.create(
                        location_id=location_id,
                        user_id=user_id,
                        booking_group_id=booking_group.id,
                        location_service_day_id=location_service_day_id,
                        child_id=selection.child_id,
                        price_snapshot_cents=pricing.current_price_cents,
                        currency=pricing.currency,
                        booking_status="PENDING",
                    )
                )

        # Bookings hold their places as PENDING until the Stripe webhook
        # confirms or expires them (app/integrations/payments/stripe/webhook.py).
        checkout = self._start_checkout(
            booking_group=booking_group,
            bookings=bookings,
            resolved_service_days=resolved_service_days,
            site_url=site_url,
        )

        return CreateBookingResponse(
            idempotency_key=booking_group.idempotency_key,
            booking_group_id=booking_group.id,
            amount=sum(
                booking.price_snapshot_cents
                for booking in bookings
            ),
            checkout_url=checkout.checkout_url,
        )

    @transactional
    def create_checkout_for_group(
        self,
        *,
        booking_group_id: UUID,
        user_id: UUID,
        location_id: UUID,
        origin: str | None,
    ) -> CheckoutUrlResponse:
        """
        Continue to payment for a pending group (from the review screen):
        its open Stripe session, or a new one if that session has expired.
        """
        self._require_complete_profile(user_id=user_id)

        site_url = self._site_url(
            location_id=location_id,
            origin=origin,
        )

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

        # Expired (including a lapsed hold) or cancelled: its places may be
        # gone, so it has to be booked again.
        if status != BookingStatus.PENDING:
            raise BookingAttemptFinishedError()

        bookings = self.booking_repository.list_by_booking_group_id(
            booking_group_id=booking_group.id,
        )

        resolved_service_days = (
            self.location_service_repository.list_by_service_day_ids(
                ids=[booking.location_service_day_id for booking in bookings],
            )
        )

        checkout = self._resume_checkout(
            pending=PendingBookingGroup(
                booking_group=booking_group,
                bookings=bookings,
                amount=sum(
                    booking.price_snapshot_cents
                    for booking in bookings
                ),
            ),
            resolved_service_days=resolved_service_days,
            site_url=site_url,
        )

        return CheckoutUrlResponse(checkout_url=checkout.checkout_url)

    def _require_complete_profile(
        self,
        *,
        user_id: UUID,
    ) -> None:
        """
        Bookings need the parent's contact details (the same rule as adding
        a child). Checked on every booking and payment, not just when the
        child was added, since the profile can be cleared afterwards.
        """
        missing_fields = self.customer_profile_repository.get_missing_fields_for_user(
            user_id=user_id,
        )

        if missing_fields:
            raise CustomerProfileIncompleteError(
                missing_fields=missing_fields,
            )

    def _site_url(
        self,
        *,
        location_id: UUID,
        origin: str | None,
    ) -> str:
        """
        The location's frontend URL, for Stripe's return links. Built from
        the request's Origin (so dev ports work) but only once it's checked
        to be this tenant's site, so it can't be used as an open redirect.
        """
        location = self.location_repository.get_by_id(id=location_id)
        tenant = self.tenant_repository.get_by_id(id=location.tenant_id)

        hostname = (urlparse(origin).hostname or "").lower() if origin else ""

        allowed_hostnames = {
            f"{tenant.code}.{settings.BASE_DOMAIN}".lower(),
        }

        if tenant.custom_domain:
            allowed_hostnames.add(tenant.custom_domain.lower())

        if hostname not in allowed_hostnames:
            raise CheckoutOriginError()

        return f"{origin.rstrip('/')}/{location.code}"

    def _start_checkout(
        self,
        *,
        booking_group: BookingGroup,
        bookings: list[Booking],
        resolved_service_days,
        site_url: str,
    ) -> StripeCheckout:
        days_by_id = {
            day.location_service_day_id: day
            for day in resolved_service_days
        }

        currency = bookings[0].currency

        attempt = self.payment_attempt_repository.create(
            location_id=booking_group.location_id,
            user_id=booking_group.user_id,
            booking_group_id=booking_group.id,
            total_cents=sum(
                booking.price_snapshot_cents
                for booking in bookings
            ),
            currency=currency,
        )

        line_items = []

        for booking in bookings:
            day = days_by_id.get(booking.location_service_day_id)

            line_items.append(
                CheckoutLineItem(
                    description=(
                        f"{day.service_name} - {day.service_date:%a %d %b %Y}"
                        if day
                        else "Booking"
                    ),
                    amount_cents=booking.price_snapshot_cents,
                )
            )

        # The webhook acts as this user at this location (for RLS) and finds
        # the attempt from this metadata.
        checkout = self.stripe.create_checkout_session(
            line_items=line_items,
            currency=currency,
            metadata={
                "booking_group_id": str(booking_group.id),
                "payment_attempt_id": str(attempt.id),
                "user_id": str(booking_group.user_id),
                "location_id": str(booking_group.location_id),
            },
            success_url=(
                f"{site_url}/bookings/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{site_url}/bookings/new",
            # One Stripe session per attempt, even if this request is retried.
            idempotency_key=f"checkout-{attempt.id}",
        )

        attempt.stripe_checkout_session_id = checkout.checkout_session_id
        attempt.stripe_payment_intent_id = checkout.payment_intent_id

        return checkout

    def _resume_checkout(
        self,
        *,
        pending: PendingBookingGroup,
        resolved_service_days,
        site_url: str,
    ) -> StripeCheckout:
        """The group's open checkout, or a fresh one if it has expired."""
        latest = self.payment_attempt_repository.get_latest_by_booking_group_id(
            booking_group_id=pending.booking_group.id,
        )

        if latest and latest.stripe_checkout_session_id:
            checkout = self.stripe.get_checkout_session(
                checkout_session_id=latest.stripe_checkout_session_id,
            )

            if checkout.status == "open":
                return checkout

        return self._start_checkout(
            booking_group=pending.booking_group,
            bookings=pending.bookings,
            resolved_service_days=resolved_service_days,
            site_url=site_url,
        )

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
            BookingConflictRow.model_validate(
                conflict,
                from_attributes=True,
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