from uuid import UUID

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import (
    Booking,
    ChildDocument,
    ChildMedicalState,
    ChildProfile,
    CustomerProfile,
    Location,
    LocationServiceDay,
    User,
)
from app.public.schemas.enums import ChildDocumentUploadStatus, MedicalReviewStatus


class ChildMedicalStateRepository(Repository):
    def create(
        self,
        *,
        child_id: UUID,
        review_status: MedicalReviewStatus = MedicalReviewStatus.NOT_REQUIRED,
        updated_at=None,
        updated_by_user_id: UUID | None = None,
    ) -> ChildMedicalState:
        record = ChildMedicalState(
            child_id=child_id,
            review_status=review_status,
            updated_at=updated_at,
            updated_by_user_id=updated_by_user_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> ChildMedicalState | None:
        return (
            self.db.query(ChildMedicalState)
            .filter(ChildMedicalState.child_id == id)
            .first()
        )

    def decide(
        self,
        *,
        state: ChildMedicalState,
        review_status: str,
        documentation_request: str | None,
    ) -> ChildMedicalState:
        """
        Record a staff decision. trg_child_medical_state_rules (schema/0004)
        checks it, records the reviewer and clears the request on approval.
        """
        state.review_status = review_status
        state.documentation_request = documentation_request

        self.db.flush()

        return state

    def reopen(
        self,
        *,
        child_id: UUID,
    ) -> int:
        """
        An approved child back to pending (0 rows if they aren't approved:
        a no-op change would slip past trg_child_medical_state_rules,
        which checks changes). The trigger clears the reviewer.
        """
        return (
            self.db.query(ChildMedicalState)
            .filter(
                ChildMedicalState.child_id == child_id,
                ChildMedicalState.review_status == MedicalReviewStatus.APPROVED,
            )
            .update(
                {
                    ChildMedicalState.review_status: MedicalReviewStatus.PENDING,
                    ChildMedicalState.documentation_request: None,
                },
                synchronize_session=False,
            )
        )

    def get_review(
        self,
        *,
        child_id: UUID,
    ) -> Row | None:
        return (
            self._review_query(
                ChildProfile.is_active,
                ChildProfile.medical_info,
                ChildProfile.allergy_info,
                ChildProfile.medication_info,
                ChildMedicalState.updated_by_user_id.label("reviewed_by_user_id"),
                User.id.label("family_user_id"),
                User.email.label("family_email"),
                self._upcoming_bookings().label("upcoming_bookings"),
            )
            .filter(ChildProfile.id == child_id)
            .first()
        )

    def list_reviews(
        self,
        *,
        review_status: list[str],
        text_query: str | None = None,
        newest_first: bool = False,
    ) -> list[Row]:
        """
        Current children in the given statuses, longest waiting first (or
        newest decision first, for the approved list). text_query matches
        the start of the child's or the parent's first or last name, or
        their full name.
        """
        document_count = (
            self.db.query(func.count(ChildDocument.id))
            .filter(
                ChildDocument.child_id == ChildProfile.id,
                ChildDocument.is_active.is_(True),
                ChildDocument.upload_status == ChildDocumentUploadStatus.UPLOADED,
            )
            .correlate(ChildProfile)
            .scalar_subquery()
        )

        return (
            self._review_query(
                document_count.label("document_count"),
            )
            .filter(
                ChildProfile.is_active.is_(True),
                ChildMedicalState.review_status.in_(review_status),
                *([self._name_matches(text_query)] if text_query else []),
            )
            .order_by(
                func.coalesce(ChildMedicalState.updated_at, ChildProfile.created_at).desc()
                if newest_first
                else "status_since",
                ChildProfile.first_name,
                ChildProfile.last_name,
            )
            .all()
        )

    @staticmethod
    def _name_matches(text_query: str):
        """The child's or the parent's name starts with the text (any word, or the full name)."""
        pattern = f"{text_query.lower()}%"
        names = (
            ChildProfile.first_name,
            ChildProfile.last_name,
            ChildProfile.first_name + " " + ChildProfile.last_name,
            User.first_name,
            User.last_name,
            User.first_name + " " + User.last_name,
        )

        return or_(*(func.lower(name).like(pattern) for name in names))

    @staticmethod
    def _upcoming_bookings():
        """The child's confirmed bookings from today on (location time)."""
        return (
            select(func.count(Booking.id))
            .join(LocationServiceDay, LocationServiceDay.id == Booking.location_service_day_id)
            .join(Location, Location.id == Booking.location_id)
            .where(
                Booking.child_id == ChildProfile.id,
                Booking.booking_status == "CONFIRMED",
                LocationServiceDay.service_date >= cast(func.timezone(Location.timezone, func.now()), Date),
            )
            .correlate(ChildProfile)
            .scalar_subquery()
        )

    def _review_query(self, *columns):
        # A new child's state has no updated_at until it first changes.
        status_since = func.coalesce(
            ChildMedicalState.updated_at,
            ChildProfile.created_at,
        )

        return (
            self.db.query(
                ChildProfile.id.label("child_id"),
                ChildProfile.first_name,
                ChildProfile.last_name,
                ChildProfile.dob,
                ChildMedicalState.review_status,
                ChildMedicalState.documentation_request,
                status_since.label("status_since"),
                # Who made the latest decision, as "Sam L."; None while waiting.
                func.public.staff_short_name(ChildMedicalState.updated_by_user_id).label("reviewed_by"),
                User.first_name.label("family_first_name"),
                User.last_name.label("family_last_name"),
                CustomerProfile.phone.label("family_phone"),
                *columns,
            )
            .join(
                ChildMedicalState,
                ChildMedicalState.child_id == ChildProfile.id,
            )
            .join(
                User,
                User.id == ChildProfile.user_id,
            )
            .outerjoin(
                CustomerProfile,
                CustomerProfile.user_id == ChildProfile.user_id,
            )
        )
