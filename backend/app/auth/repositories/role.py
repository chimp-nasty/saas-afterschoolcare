from uuid import UUID

from app.db.repository import Repository
from app.auth.models.role import Role


class RoleRepository(Repository):
    def create(
        self,
        *,
        code: str,
        name: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> Role:
        record = Role(
            code=code,
            name=name,
            description=description,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.id == id)
            .first()
        )

    def get_by_code(
        self,
        *,
        code: str
    ) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.code == code)
            .first()
        )

    def list_by_ids(
        self,
        *,
        role_ids: list[UUID],
    ) -> list[Role]:
        return (
            self.db.query(Role)
            .filter(
                Role.id.in_(role_ids),
            )
            .all()
        )