import logging
from datetime import date, datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Location
from app.db.transaction import transactional
from app.errors.attendance import AttendanceNotSignedInError
from app.errors.base import ApplicationError
from app.errors.database import map_integrity_error
from app.errors.bookings import BookingNotFoundError
from app.public.repositories.attendance_record import AttendanceRecordRepository
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.repositories.booking import BookingRepository
from app.public.repositories.child_profile import ChildProfileRepository
from app.public.schemas.attendance import (
    AttendanceTimesResponse,
    RollEntryResponse,
    RollFamilyResponse,
    RollPickupPersonResponse,
    RollResponse,
    RunSheetEntryResponse,
    RunSheetResponse,
    RunSheetSessionResponse,
)
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.attendance")


def location_today(location: Location) -> date:
    """Today's date where the location is."""
    return datetime.now(ZoneInfo(location.timezone)).date()


def to_pickup_person(person) -> RollPickupPersonResponse:
    return RollPickupPersonResponse(
        pickup_person_id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        relation=getattr(person.relation, "value", person.relation),
        phone=person.phone,
        identity_verified_at=person.identity_verified_at,
        staff_approved_at=person.staff_approved_at,
    )


class ReadAttendanceService:
    """
    A day's roll, with each booked family's pickup list (who may collect,
    and who's approved). The same service behind the admin run sheet and the
    staff kiosk (docs/portals.md, section 4): RLS and attendance_roll decide
    who gets rows (admins on the website, staff only at the staff kiosk).
    """

    def __init__(
        self,
        *,
        db: Session,
        attendance_repository: AttendanceRecordRepository,
        pickup_repository: AuthorizedPickupPersonRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.attendance_repository = attendance_repository
        self.pickup_repository = pickup_repository
        self.location_repository = location_repository

    def roll(
        self,
        *,
        location_id: UUID,
        on: date | None,
    ) -> RollResponse:
        on = on or location_today(self.location_repository.get_by_id(id=location_id))

        rows = self.attendance_repository.roll(location_id=location_id, on=on)

        entries = [RollEntryResponse.model_validate(row, from_attributes=True) for row in rows]
        family_ids = sorted({entry.family_user_id for entry in entries})
        people = self.pickup_repository.list_for_families(user_ids=family_ids, location_id=location_id)

        return RollResponse(
            date=on,
            entries=entries,
            families=[
                RollFamilyResponse(
                    family_user_id=family_id,
                    pickups=[to_pickup_person(p) for p in people if p.user_id == family_id],
                )
                for family_id in family_ids
            ],
        )

    def run_sheet(
        self,
        *,
        location_id: UUID,
        on: date | None,
    ) -> RunSheetResponse:
        """The run sheet as the staff kiosk shows it, for the admin run sheet (read-only)."""
        on = on or location_today(self.location_repository.get_by_id(id=location_id))
        sessions, rows = self.attendance_repository.run_sheet(location_id=location_id, on=on)

        return RunSheetResponse(
            date=on,
            sessions=[RunSheetSessionResponse.model_validate(row, from_attributes=True) for row in sessions],
            entries=[RunSheetEntryResponse.model_validate(row, from_attributes=True) for row in rows],
        )

    def family_pickups(
        self,
        *,
        location_id: UUID,
        family_user_id: UUID,
    ) -> list[RollPickupPersonResponse]:
        people = self.pickup_repository.list_for_families(user_ids=[family_user_id], location_id=location_id)

        return [to_pickup_person(p) for p in people]


class UpdateAttendanceService:
    """
    A staff member signing children in and out at the staff kiosk (missed
    sign-ins, children arriving from school, collections, one-off releases,
    sending before school children to school) and correcting mistakes. Runs
    as them on the kiosk channel; the database allows it only there,
    records them and the device, and checks the rules
    (trg_attendance_records_rules, docs/kiosk-procedures.md section 5).

    The bulk actions (signing in a session's arrivals, sending a before
    school session to school) are all or nothing: if one child can't be
    done, none are, and the error names the child.
    """

    def __init__(
        self,
        *,
        db: Session,
        attendance_repository: AttendanceRecordRepository,
        booking_repository: BookingRepository,
        child_repository: ChildProfileRepository,
    ):
        self.db = db
        self.attendance_repository = attendance_repository
        self.booking_repository = booking_repository
        self.child_repository = child_repository

    @transactional
    def sign_in(
        self,
        *,
        booking_id: UUID,
        at: datetime | None,
    ) -> AttendanceTimesResponse:
        self._get_booking(booking_id=booking_id)

        return self._sign_in(booking_id=booking_id, at=self._when(at))

    @transactional
    def sign_out(
        self,
        *,
        booking_id: UUID,
        at: datetime | None,
        collected_by_pickup_person_id: UUID | None = None,
        released_to_name: str | None = None,
        release_note: str | None = None,
        sent_to_school: bool = False,
    ) -> AttendanceTimesResponse:
        self._get_booking(booking_id=booking_id)

        return self._sign_out(
            booking_id=booking_id,
            at=self._when(at),
            collected_by_pickup_person_id=collected_by_pickup_person_id,
            released_to_name=released_to_name,
            release_note=release_note,
            sent_to_school=sent_to_school,
        )

    @transactional
    def sign_in_many(
        self,
        *,
        booking_ids: list[UUID],
        at: datetime | None,
    ) -> list[AttendanceTimesResponse]:
        when = self._when(at)

        return self._each(booking_ids, lambda booking_id: self._sign_in(booking_id=booking_id, at=when))

    @transactional
    def send_to_school(
        self,
        *,
        booking_ids: list[UUID],
        at: datetime | None,
    ) -> list[AttendanceTimesResponse]:
        when = self._when(at)

        return self._each(
            booking_ids,
            lambda booking_id: self._sign_out(booking_id=booking_id, at=when, sent_to_school=True),
        )

    @transactional
    def sign_out_many(
        self,
        *,
        booking_ids: list[UUID],
        at: datetime | None,
        collected_by_pickup_person_id: UUID | None = None,
        released_to_name: str | None = None,
        release_note: str | None = None,
    ) -> list[AttendanceTimesResponse]:
        """Brothers and sisters, to the same person."""
        when = self._when(at)

        return self._each(
            booking_ids,
            lambda booking_id: self._sign_out(
                booking_id=booking_id,
                at=when,
                collected_by_pickup_person_id=collected_by_pickup_person_id,
                released_to_name=released_to_name,
                release_note=release_note,
            ),
        )

    @transactional
    def undo(
        self,
        *,
        booking_id: UUID,
        step: str,
    ) -> AttendanceTimesResponse:
        self._get_booking(booking_id=booking_id)

        if step == "sign_out":
            self.attendance_repository.clear_sign_out(booking_id=booking_id)
        else:
            self.attendance_repository.clear_sign_in(booking_id=booking_id)

        # Undo leaves no trace in attendance, so the log is its record.
        self._log(f"attendance_undo_{step}", booking_id)

        return self._times(booking_id=booking_id)

    def _sign_in(self, *, booking_id: UUID, at: datetime) -> AttendanceTimesResponse:
        self.attendance_repository.sign_in(booking_id=booking_id, at=at)
        self._log("attendance_sign_in", booking_id)

        return self._times(booking_id=booking_id)

    def _sign_out(
        self,
        *,
        booking_id: UUID,
        at: datetime,
        collected_by_pickup_person_id: UUID | None = None,
        released_to_name: str | None = None,
        release_note: str | None = None,
        sent_to_school: bool = False,
    ) -> AttendanceTimesResponse:
        signed_out = self.attendance_repository.sign_out(
            booking_id=booking_id,
            at=at,
            collected_by_pickup_person_id=collected_by_pickup_person_id,
            released_to_name=released_to_name,
            release_note=release_note,
            sent_to_school=sent_to_school,
        )

        times = self._times(booking_id=booking_id)

        # Already signed out: nothing more to do. Never signed in: staff
        # should check, as the child may not be here.
        if not signed_out and not times.signed_out_at:
            raise AttendanceNotSignedInError()

        if released_to_name:
            self._log("attendance_sign_out_one_off_release", booking_id)
        elif sent_to_school:
            self._log("attendance_sign_out_to_school", booking_id)
        else:
            self._log("attendance_sign_out", booking_id)

        return times

    def _each(self, booking_ids: list[UUID], act) -> list[AttendanceTimesResponse]:
        """
        Does `act` for each booking, in this one transaction. The first one
        that fails stops the lot (rolled back) with an error naming the
        child; names are looked up first, as a failed statement ends the
        transaction.
        """
        names = {}

        for booking_id in booking_ids:
            booking = self._get_booking(booking_id=booking_id)
            child = self.child_repository.get_by_id(id=booking.child_id)
            names[booking_id] = child.first_name if child else "A child"

        results = []

        for booking_id in booking_ids:
            try:
                results.append(act(booking_id))
            except IntegrityError as exc:
                error = map_integrity_error(exc)

                if not isinstance(error, ApplicationError):
                    raise

                raise type(error)(message=f"{names[booking_id]}: {error.message}", log_reason=error.log_reason) from exc
            except ApplicationError as error:
                raise type(error)(message=f"{names[booking_id]}: {error.message}", log_reason=error.log_reason) from error

        return results

    def _get_booking(self, *, booking_id: UUID):
        # RLS: only this location's bookings (for staff, only at the kiosk).
        booking = self.booking_repository.get_by_id(id=booking_id)

        if not booking:
            raise BookingNotFoundError()

        return booking

    def _when(self, at: datetime | None) -> datetime:
        # When it happened (a missed one), never in the future.
        now = datetime.now(timezone.utc)

        return min(at, now) if at else now

    def _times(self, *, booking_id: UUID) -> AttendanceTimesResponse:
        row = self.attendance_repository.get_times(booking_id=booking_id)

        return AttendanceTimesResponse(
            booking_id=booking_id,
            signed_in_at=row.signed_in_at if row else None,
            signed_out_at=row.signed_out_at if row else None,
        )

    def _log(self, event: str, booking_id: UUID) -> None:
        logger.info(
            "Attendance changed",
            extra={"event": event, "result": "success", "reason": f"booking_id={booking_id}"},
        )
