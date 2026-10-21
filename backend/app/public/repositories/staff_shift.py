from datetime import datetime
from uuid import UUID

from sqlalchemy import func, text

from app.db.repository import Repository
from app.db.models import StaffShift


class StaffShiftRepository(Repository):
    """
    Staff shifts under RLS: a staff member starts and ends their own, only
    at the staff kiosk (staff_shifts_kiosk_write_policy, schema/0007); the
    device is recorded by trg_staff_shifts_device.
    """

    def is_on_shift(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> bool:
        """An open shift started on the location's today (public.staff_on_shift)."""
        return self.db.execute(
            text("SELECT public.staff_on_shift(:location_id, :user_id)"),
            {"location_id": location_id, "user_id": user_id},
        ).scalar_one()

    def get_open(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> StaffShift | None:
        return (
            self.db.query(StaffShift)
            .filter(
                StaffShift.location_id == location_id,
                StaffShift.user_id == user_id,
                StaffShift.ended_at.is_(None),
            )
            .first()
        )

    def start(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        device_id: UUID,
    ) -> StaffShift:
        shift = StaffShift(
            location_id=location_id,
            user_id=user_id,
            started_kiosk_device_id=device_id,
        )

        self.db.add(shift)
        self.db.flush()

        return shift

    def end(
        self,
        *,
        shift: StaffShift,
        device_id: UUID,
        at: datetime | None = None,
    ) -> StaffShift:
        # The database's clock unless a time was given: the start is the
        # database's too (ck_staff_shifts_ended_after_started).
        shift.ended_at = at or func.now()
        shift.ended_kiosk_device_id = device_id

        self.db.flush()
        self.db.refresh(shift)

        return shift
