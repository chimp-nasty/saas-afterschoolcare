from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row

from app.db.models import LocationUserRole, Role
from app.db.repository import Repository


class StaffAccountRepository(Repository):
    """
    A location's staff accounts (schema/0004, STAFF ACCOUNTS). Admins can't
    read each other's accounts or PINs under RLS, so the list, names, PIN
    resets and removals go through functions that check the session user
    manages this location's staff first. Role changes are plain writes to
    auth.location_user_roles, which trg_location_user_roles_staff_rules
    guards (no superadmins, not yourself, never the last admin).
    """

    def list(
        self,
        *,
        location_id: UUID,
    ) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.location_staff(:location_id)"),
            {"location_id": location_id},
        ).all()

    def can_manage(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> bool:
        return self.db.execute(
            text("SELECT public.can_manage_location_staff(:location_id, :user_id)"),
            {"location_id": location_id, "user_id": user_id},
        ).scalar_one()

    def set_name(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        self.db.execute(
            text("SELECT public.set_staff_name(:location_id, :user_id, :first_name, :last_name)"),
            {"location_id": location_id, "user_id": user_id, "first_name": first_name, "last_name": last_name},
        )

    def reset_pin(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> None:
        self.db.execute(
            text("SELECT public.reset_staff_pin(:location_id, :user_id)"),
            {"location_id": location_id, "user_id": user_id},
        )

    def remove(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> None:
        self.db.execute(
            text("SELECT public.remove_location_staff(:location_id, :user_id)"),
            {"location_id": location_id, "user_id": user_id},
        )

    def staff_role(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> LocationUserRole | None:
        """Their staff or admin role at the location."""
        return (
            self.db.query(LocationUserRole)
            .join(Role, Role.id == LocationUserRole.role_id)
            .filter(
                LocationUserRole.location_id == location_id,
                LocationUserRole.user_id == user_id,
                Role.code.in_(["staff", "admin"]),
            )
            .first()
        )

    def set_role(
        self,
        *,
        role_row: LocationUserRole,
        role_id: UUID,
    ) -> None:
        role_row.role_id = role_id
        self.db.flush()
