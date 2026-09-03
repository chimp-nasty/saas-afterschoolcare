from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.models.permission import Permission
from app.auth.models.role_permission import RolePermission


class PermissionRepository:
    def __init__(self, *, db: Session):
        self.db = db

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
        role_ids: list[UUID]
    ) -> list[Permission]:
        return (
            self.db.query(Permission)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .filter(
                RolePermission.role_id.in_(role_ids),
            )
            .distinct()
            .all()
        )