import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.repositories.staff_pin import StaffPinRepository
from app.auth.repositories.user import UserRepository
from app.auth.schemas.staff_pin import SetStaffPinRequest, StaffPinStatusResponse
from app.core.security import verify_password
from app.db.transaction import transactional
from app.errors.kiosk import StaffPinPasswordError


logger = logging.getLogger("app.auth")


class StaffPinService:
    """
    A staff member's own PIN for the staff kiosk (docs/kiosk-procedures.md,
    section 3). Set only here, never at the kiosk, and only after
    re-entering their password: otherwise anyone at their logged-in browser
    could set a PIN and act as them at the kiosk.
    """

    def __init__(
        self,
        *,
        db: Session,
        users: UserRepository,
        staff_pins: StaffPinRepository,
    ):
        self.db = db
        self.users = users
        self.staff_pins = staff_pins

    def status(
        self,
        *,
        user_id: UUID,
    ) -> StaffPinStatusResponse:
        pin = self.staff_pins.get_by_user_id(user_id=user_id)

        return StaffPinStatusResponse(
            is_set=pin is not None,
            set_at=pin.set_at if pin else None,
            is_locked=bool(pin and pin.pin_locked_at),
        )

    @transactional
    def set(
        self,
        *,
        user_id: UUID,
        body: SetStaffPinRequest,
    ) -> StaffPinStatusResponse:
        # RLS: a user always sees their own row.
        user = self.users.get_by_id(id=user_id)

        if not user or not verify_password(password=body.password, hashed_password=user.password_hash):
            raise StaffPinPasswordError()

        self.staff_pins.set_own(pin=body.pin)

        logger.info(
            "Staff PIN set",
            extra={
                "event": "staff_pin_set",
                "result": "success",
                "reason": f"user_id={user_id}",
            },
        )

        return self.status(user_id=user_id)
