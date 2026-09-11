from uuid import UUID

from app.db.repository import Repository
from app.auth.models.location_user_role import LocationUserRole


class LocationUserRoleRepository(Repository):
    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        role_id: UUID,
    ) -> LocationUserRole:
        record = LocationUserRole(
            user_id=user_id,
            location_id=location_id,
            role_id=role_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> LocationUserRole | None:
        return (
            self.db.query(LocationUserRole)
            .filter(LocationUserRole.id == id)
            .first()
        )

    def list_roles_by_user_and_location(
        self,
        *,
        user_id: UUID,
        location_id: UUID
    ) -> list[LocationUserRole]:
        return (
            self.db.query(LocationUserRole)
            .filter(
                LocationUserRole.user_id == user_id,
                LocationUserRole.location_id == location_id,
            )
            .all()
        )

    def list_by_user(
        self,
        *,
        user_id: UUID
    ) -> list[LocationUserRole]:
        return (
            self.db.query(LocationUserRole)
            .filter(
                LocationUserRole.user_id == user_id,
            )
            .all()
        )