from uuid import UUID

from app.db.repository import Repository
from app.auth.models.role_permission import RolePermission


class RolePermissionRepository(Repository):
    def create(
        self,
        *,
        role_id: UUID,
        permission_id: UUID,
    ) -> RolePermission:
        record = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> RolePermission | None:
        return (
            self.db.query(RolePermission)
            .filter(RolePermission.id == id)
            .first()
        )
