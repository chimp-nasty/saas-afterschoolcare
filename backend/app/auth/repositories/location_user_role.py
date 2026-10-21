from uuid import UUID

from app.db.repository import Repository
from app.db.models import Location, LocationUserRole, Role


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

    def list_with_locations(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
    ) -> list[tuple[Location, Role]]:
        """A user's roles at a tenant's locations, by location then role."""
        return (
            self.db.query(Location, Role)
            .join(LocationUserRole, LocationUserRole.location_id == Location.id)
            .join(Role, Role.id == LocationUserRole.role_id)
            .filter(
                LocationUserRole.user_id == user_id,
                Location.tenant_id == tenant_id,
            )
            .order_by(Location.name, Location.code, Role.name)
            .all()
        )
