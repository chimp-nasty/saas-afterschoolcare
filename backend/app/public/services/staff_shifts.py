import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.public.repositories.staff_shift import StaffShiftRepository
from app.errors.kiosk import StaffShiftEndTimeInvalidError, StaffShiftEndTimeRequiredError
from app.public.schemas.attendance import StaffShiftResponse


logger = logging.getLogger("app.staff")


class StaffShiftService:
    """
    A staff member starting or ending their shift at the staff kiosk (the
    only place it's allowed: staff_shifts_kiosk_write_policy). Starting while
    on shift, or ending while off, changes nothing.

    A shift left open from an earlier day doesn't count as on shift
    (public.staff_on_shift). Clocking in again first closes it with the time
    they say they left; nothing is invented for timesheets.
    """

    def __init__(
        self,
        *,
        db: Session,
        shift_repository: StaffShiftRepository,
    ):
        self.db = db
        self.shift_repository = shift_repository

    @transactional
    def start(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        device_id: UUID,
        previous_shift_ended_at: datetime | None = None,
    ) -> StaffShiftResponse:
        shift = self.shift_repository.get_open(location_id=location_id, user_id=user_id)

        if shift and not self.shift_repository.is_on_shift(location_id=location_id, user_id=user_id):
            self._close_forgotten(shift=shift, device_id=device_id, ended_at=previous_shift_ended_at)
            shift = None

        if not shift:
            shift = self.shift_repository.start(location_id=location_id, user_id=user_id, device_id=device_id)
            self._log("staff_shift_started", user_id)

        return StaffShiftResponse(started_at=shift.started_at, ended_at=None)

    @transactional
    def end(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        device_id: UUID,
    ) -> StaffShiftResponse:
        shift = self.shift_repository.get_open(location_id=location_id, user_id=user_id)

        # Only today's shift: a forgotten one is closed when they next clock in.
        if not shift or not self.shift_repository.is_on_shift(location_id=location_id, user_id=user_id):
            return StaffShiftResponse(started_at=None, ended_at=None)

        shift = self.shift_repository.end(shift=shift, device_id=device_id)
        self._log("staff_shift_ended", user_id)

        return StaffShiftResponse(started_at=shift.started_at, ended_at=shift.ended_at)

    def _close_forgotten(self, *, shift, device_id: UUID, ended_at: datetime | None) -> None:
        if ended_at is None:
            raise StaffShiftEndTimeRequiredError()

        if ended_at < shift.started_at or ended_at > datetime.now(timezone.utc):
            raise StaffShiftEndTimeInvalidError()

        self.shift_repository.end(shift=shift, device_id=device_id, at=ended_at)
        self._log("staff_shift_closed_late", shift.user_id)

    def _log(self, event: str, user_id: UUID) -> None:
        logger.info("Staff shift", extra={"event": event, "result": "success", "reason": f"user_id={user_id}"})
