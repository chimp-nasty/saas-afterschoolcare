from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row

from app.db.repository import Repository


class AttendanceRecordRepository(Repository):
    """
    Attendance under RLS. Writes only succeed at a kiosk:
    trg_attendance_records_rules refuses any web session, and records the
    staff member and device from the kiosk channel (docs/portals.md). The
    family kiosk writes through its own kiosk_* functions instead.
    """

    def roll(
        self,
        *,
        location_id: UUID,
        on: date,
    ) -> list[Row]:
        """A day's roll (public.attendance_roll: admins, or staff at the kiosk)."""
        return self.db.execute(
            text("SELECT * FROM public.attendance_roll(:location_id, :on)"),
            {"location_id": location_id, "on": on},
        ).all()

    def run_sheet(
        self,
        *,
        location_id: UUID,
        on: date,
    ) -> tuple[list[Row], list[Row]]:
        """A day's sessions and rows (public.run_sheet_sessions / run_sheet_board)."""
        where = {"location_id": location_id, "on": on}
        sessions = self.db.execute(text("SELECT * FROM public.run_sheet_sessions(:location_id, :on)"), where).all()
        rows = self.db.execute(text("SELECT * FROM public.run_sheet_board(:location_id, :on)"), where).all()

        return sessions, rows

    def get_times(
        self,
        *,
        booking_id: UUID,
    ) -> Row | None:
        return self.db.execute(
            text("SELECT signed_in_at, signed_out_at FROM public.attendance_records WHERE booking_id = :booking_id"),
            {"booking_id": booking_id},
        ).first()

    def sign_in(
        self,
        *,
        booking_id: UUID,
        at: datetime | None,
    ) -> None:
        """
        Signed in at `at` (None: now, by the database's clock, like the
        family kiosk's), unless it already is (who and where: the trigger).
        """
        self.db.execute(
            text("""
                INSERT INTO public.attendance_records (booking_id, signed_in_at)
                VALUES (:booking_id, COALESCE(CAST(:at AS timestamptz), now()))
                ON CONFLICT (booking_id) DO UPDATE
                SET signed_in_at = EXCLUDED.signed_in_at
                WHERE attendance_records.signed_in_at IS NULL
            """),
            {"booking_id": booking_id, "at": at},
        )

    def sign_out(
        self,
        *,
        booking_id: UUID,
        at: datetime | None,
        collected_by_pickup_person_id: UUID | None,
        released_to_name: str | None,
        release_note: str | None,
        sent_to_school: bool = False,
    ) -> bool:
        """Signed out if it's signed in and not yet out; False otherwise."""
        result = self.db.execute(
            text("""
                UPDATE public.attendance_records
                SET signed_out_at = COALESCE(CAST(:at AS timestamptz), now()),
                    collected_by_pickup_person_id = :collected_by,
                    released_to_name = :released_to,
                    release_note = :note,
                    sent_to_school = :to_school
                WHERE booking_id = :booking_id
                  AND signed_in_at IS NOT NULL
                  AND signed_out_at IS NULL
            """),
            {
                "booking_id": booking_id,
                "at": at,
                "collected_by": collected_by_pickup_person_id,
                "released_to": released_to_name,
                "note": release_note,
                "to_school": sent_to_school,
            },
        )

        return result.rowcount == 1

    def clear_sign_out(
        self,
        *,
        booking_id: UUID,
    ) -> None:
        self.db.execute(
            text("""
                UPDATE public.attendance_records
                SET signed_out_at = NULL,
                    signed_out_by_user_id = NULL,
                    signed_out_kiosk_device_id = NULL,
                    collected_by_pickup_person_id = NULL,
                    released_to_name = NULL,
                    release_note = NULL,
                    sent_to_school = FALSE
                WHERE booking_id = :booking_id
            """),
            {"booking_id": booking_id},
        )

    def clear_sign_in(
        self,
        *,
        booking_id: UUID,
    ) -> None:
        """Only while not signed out (clear the sign-out first)."""
        self.db.execute(
            text("""
                UPDATE public.attendance_records
                SET signed_in_at = NULL,
                    signed_in_by_user_id = NULL,
                    signed_in_by_pickup_person_id = NULL,
                    signed_in_kiosk_device_id = NULL
                WHERE booking_id = :booking_id
                  AND signed_out_at IS NULL
            """),
            {"booking_id": booking_id},
        )
