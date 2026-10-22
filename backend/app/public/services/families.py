import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.customer import FamilyNotFoundError
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.repositories.booking import BookingRepository
from app.public.repositories.customer_profile import CustomerProfileRepository
from app.public.repositories.family import FamilyRepository
from app.public.schemas.booking import FamilyBookingResponse
from app.public.schemas.customer import UpdateContactDetailsRequest
from app.public.schemas.families import (
    FamilyAttendanceResponse,
    FamilyChildResponse,
    FamilyDateRangeRequest,
    FamilyPaymentResponse,
    FamilyResponse,
    FamilySearchResultResponse,
)
from app.public.services.attendance import location_today, to_pickup_person
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.families")

# The default ranges when none is chosen.
BOOKINGS_BACK_DAYS = 30
BOOKINGS_AHEAD_DAYS = 90
ATTENDANCE_BACK_DAYS = 28


class FamilyService:
    """
    Admin › Families (slice 4-4): finding a family at this centre and its
    page: the parent's details (phone and address correctable; their
    emergency contact read-only, the family's own), children
    and pickup people (read-only: families manage them, ID checks are at the
    staff kiosk), bookings, attendance history and payments. Refunds go
    through the usual refund service. Permission families r/u (admins and
    superadmins); RLS scopes everything to the location.
    """

    def __init__(
        self,
        *,
        db: Session,
        family_repository: FamilyRepository,
        booking_repository: BookingRepository,
        pickup_repository: AuthorizedPickupPersonRepository,
        profile_repository: CustomerProfileRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.family_repository = family_repository
        self.booking_repository = booking_repository
        self.pickup_repository = pickup_repository
        self.profile_repository = profile_repository
        self.location_repository = location_repository

    def search(
        self,
        *,
        location_id: UUID,
        text: str,
    ) -> list[FamilySearchResultResponse]:
        return [
            FamilySearchResultResponse.model_validate(row, from_attributes=True)
            for row in self.family_repository.search(location_id=location_id, text_query=text.strip())
        ]

    def get(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> FamilyResponse:
        row = self._family(location_id=location_id, user_id=user_id)

        return FamilyResponse(
            **row._mapping,
            children=[
                FamilyChildResponse.model_validate(child, from_attributes=True)
                for child in self.family_repository.children(location_id=location_id, user_id=user_id)
            ],
            pickups=[
                to_pickup_person(person)
                for person in self.pickup_repository.list_for_families(user_ids=[user_id], location_id=location_id)
            ],
        )

    @transactional
    def update(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        body: UpdateContactDetailsRequest,
    ) -> FamilyResponse:
        """Correct a family's phone or address (their own place on their pickup list follows the phone)."""
        self._family(location_id=location_id, user_id=user_id)
        profile = self.profile_repository.get_by_user_id(user_id=user_id)

        if not profile:
            raise FamilyNotFoundError()

        self.profile_repository.update(profile=profile, fields=body.model_dump(exclude_unset=True))
        self.db.flush()
        logger.info(
            "Family details corrected",
            extra={"event": "family_profile_updated", "result": "success", "reason": f"user_id={user_id}"},
        )

        return self.get(location_id=location_id, user_id=user_id)

    def bookings(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        dates: FamilyDateRangeRequest,
    ) -> list[FamilyBookingResponse]:
        """Bookings in the range (default a month back to three ahead), and any awaiting payment."""
        self._family(location_id=location_id, user_id=user_id)
        today = self._today(location_id)
        rows = self.booking_repository.list_family_for_staff(
            user_id=user_id,
            date_from=dates.date_from or today - timedelta(days=BOOKINGS_BACK_DAYS),
            date_to=dates.date_to or today + timedelta(days=BOOKINGS_AHEAD_DAYS),
        )

        return [FamilyBookingResponse.model_validate(row, from_attributes=True) for row in rows]

    def attendance(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        dates: FamilyDateRangeRequest,
    ) -> list[FamilyAttendanceResponse]:
        """Sessions up to today in the range (default the last 4 weeks), newest first."""
        self._family(location_id=location_id, user_id=user_id)
        today = self._today(location_id)

        return [
            FamilyAttendanceResponse.model_validate(row, from_attributes=True)
            for row in self.family_repository.attendance(
                location_id=location_id,
                user_id=user_id,
                date_from=dates.date_from or today - timedelta(days=ATTENDANCE_BACK_DAYS),
                date_to=dates.date_to or today,
            )
        ]

    def payments(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> list[FamilyPaymentResponse]:
        self._family(location_id=location_id, user_id=user_id)

        return [
            FamilyPaymentResponse.model_validate(row, from_attributes=True)
            for row in self.family_repository.payments(location_id=location_id, user_id=user_id)
        ]

    def _family(self, *, location_id: UUID, user_id: UUID):
        row = self.family_repository.get(location_id=location_id, user_id=user_id)

        if not row:
            raise FamilyNotFoundError()

        return row

    def _today(self, location_id: UUID):
        return location_today(self.location_repository.get_by_id(id=location_id))
