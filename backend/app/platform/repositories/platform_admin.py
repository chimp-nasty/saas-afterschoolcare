from datetime import datetime, timezone

from app.db.repository import Repository
from app.db.models import PlatformAdmin


class PlatformAdminRepository(Repository):
    def get_by_email(
        self,
        *,
        email: str,
    ) -> PlatformAdmin | None:
        """By email while logging in (RLS: app.login_email)."""
        return (
            self.db.query(PlatformAdmin)
            .filter(PlatformAdmin.email == email)
            .first()
        )

    def update_last_login(
        self,
        *,
        platform_admin: PlatformAdmin,
    ) -> None:
        platform_admin.last_login = datetime.now(timezone.utc)
        self.db.flush()
