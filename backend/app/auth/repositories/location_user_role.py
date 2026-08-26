from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.models.location_user_role import LocationUserRole


class LocationUserRoleRepository:
    def __init__(self, *, db: Session):
        self.db = db

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
