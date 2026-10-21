from uuid import UUID

from sqlalchemy import text

from app.db.repository import Repository
from app.db.models import StaffPin


class StaffPinRepository(Repository):
    """A staff member's own kiosk PIN (RLS: only their own row is visible)."""

    def get_by_user_id(
        self,
        *,
        user_id: UUID,
    ) -> StaffPin | None:
        return (
            self.db.query(StaffPin)
            .filter(StaffPin.user_id == user_id)
            .first()
        )

    def set_own(
        self,
        *,
        pin: str,
    ) -> None:
        """Set the session user's PIN (public.set_staff_pin: staff only, 4 digits, clears a lock)."""
        self.db.execute(text("SELECT public.set_staff_pin(:pin)"), {"pin": pin})
