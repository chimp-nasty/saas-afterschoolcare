from uuid import UUID

from app.db.repository import Repository
from app.db.models import Permission, RolePermission, UserTenantPermission


class PermissionRepository(Repository):
    def create(
        self,
        *,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> Permission:
        record = Permission(
            resource=resource,
            action=action,
            description=description,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Permission | None:
        return (
            self.db.query(Permission)
            .filter(Permission.id == id)
            .first()
        )

    def list_by_role_ids(
        self,
        role_ids: list[UUID],
        channel: str = "web",
    ) -> list[Permission]:
        """
        The roles' permissions on one channel (docs/portals.md, section 2):
        "web" for a login, "kiosk" for a staff member at the staff kiosk.
        """
        return (
            self.db.query(Permission)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .filter(
                RolePermission.role_id.in_(role_ids),
                RolePermission.channel == channel,
            )
            .distinct()
            .all()
        )

    def list_tenant_permissions(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
    ) -> list[Permission]:
        """
        The user's permissions across the tenant (docs/tenant-administration.md):
        granted to its owner directly, empty for everyone else.
        """
        return (
            self.db.query(Permission)
            .join(
                UserTenantPermission,
                UserTenantPermission.permission_id == Permission.id,
            )
            .filter(
                UserTenantPermission.user_id == user_id,
                UserTenantPermission.tenant_id == tenant_id,
            )
            .all()
        )
