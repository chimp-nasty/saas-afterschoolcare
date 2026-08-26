from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.models.permission import Permission


class PermissionRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        resource: str,
        action: str,
        scope: str,
        description: str | None = None,
    ) -> Permission:
        record = Permission(
            resource=resource,
            action=action,
            scope=scope,
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
