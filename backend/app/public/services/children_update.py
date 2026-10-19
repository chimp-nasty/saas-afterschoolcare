from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ChildProfile
from app.db.transaction import transactional
from app.errors.children import (
    ChildHasUpcomingBookingsError,
    ChildProfileInactiveError,
    ChildProfileNotFoundError,
)
from app.public.repositories.booking import BookingRepository
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.children import (
    ChildResponse,
    UpdateChildRequest,
)


# Names can be changed but not cleared (the columns are NOT NULL), so an
# explicit null for one is ignored rather than failing in the database.
_REQUIRED_FIELDS = ("first_name", "last_name")


class UpdateChildService:
    """
    A family editing or removing a child. The medical review that follows a
    change to medical details happens in the database
    (trg_child_profile_medical_review, schema/0004), not here.
    """

    def __init__(
        self,
        *,
        db: Session,
        child_repository: ChildProfileRepository,
        booking_repository: BookingRepository,
    ):
        self.db = db
        self.child_repository = child_repository
        self.booking_repository = booking_repository

    @transactional
    def update(
        self,
        *,
        id: UUID,
        body: UpdateChildRequest,
    ) -> ChildResponse:
        child = self._get_active(id=id)

        values = {
            field: value
            for field, value in body.model_dump(exclude_unset=True).items()
            if not (field in _REQUIRED_FIELDS and value is None)
        }

        # A rename onto another active child of the same family is rejected
        # by the database (uq_child_profile_active_identity).
        if values:
            self.child_repository.update(
                child=child,
                values=values,
            )

        return self._response(id=child.id)

    @transactional
    def deactivate(
        self,
        *,
        id: UUID,
    ) -> ChildResponse:
        """
        Soft delete: the child stays for bookings and attendance history.
        Refused while they have upcoming bookings.
        """
        child = self._get_active(id=id)

        if self.booking_repository.has_upcoming_for_child(child_id=child.id):
            raise ChildHasUpcomingBookingsError()

        self.child_repository.deactivate(child=child)

        return self._response(id=child.id)

    def _get_active(
        self,
        *,
        id: UUID,
    ) -> ChildProfile:
        # RLS hides other families' children, so they read as not found.
        child = self.child_repository.get_by_id(id=id)

        if not child:
            raise ChildProfileNotFoundError()

        if not child.is_active:
            raise ChildProfileInactiveError()

        return child

    def _response(
        self,
        *,
        id: UUID,
    ) -> ChildResponse:
        # Read back with the review status, which the medical review
        # trigger may have just changed.
        return ChildResponse.model_validate(
            self.child_repository.get_with_context_by_id(id=id),
            from_attributes=True,
        )
