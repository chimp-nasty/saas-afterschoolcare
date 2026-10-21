from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row

from app.db.repository import Repository


class StaffKioskRepository(Repository):
    """
    What the staff kiosk needs before anyone is identified (schema/0004,
    staff_kiosk_*): the staff list, checking a PIN, and the run sheet
    without personal details. Everything else a staff member does there
    goes through the normal repositories, as them, on the kiosk channel
    (app.kiosk.dependencies.require_kiosk_staff).
    """

    def staff(
        self,
        *,
        location_id: UUID,
        device_id: UUID,
    ) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.staff_kiosk_staff(:location_id, :device_id)"),
            {"location_id": location_id, "device_id": device_id},
        ).all()

    def verify_pin(
        self,
        *,
        location_id: UUID,
        device_id: UUID,
        user_id: UUID,
        pin: str,
    ) -> str:
        """ok, invalid, locked or no_pin (a wrong PIN counts towards the lock)."""
        return self.db.execute(
            text("SELECT public.staff_kiosk_verify_pin(:location_id, :device_id, :user_id, :pin)"),
            {"location_id": location_id, "device_id": device_id, "user_id": user_id, "pin": pin},
        ).scalar_one()

    def sessions(
        self,
        *,
        location_id: UUID,
        device_id: UUID,
        on: date,
    ) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.staff_kiosk_sessions(:location_id, :device_id, :on)"),
            {"location_id": location_id, "device_id": device_id, "on": on},
        ).all()

    def board(
        self,
        *,
        location_id: UUID,
        device_id: UUID,
        on: date,
    ) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.staff_kiosk_board(:location_id, :device_id, :on)"),
            {"location_id": location_id, "device_id": device_id, "on": on},
        ).all()
