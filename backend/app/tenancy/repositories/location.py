from uuid import UUID

from sqlalchemy.orm import Session

from app.tenancy.models.location import Location


class LocationRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        code: str,
        address: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        is_active: bool = True,
    ) -> Location:
        record = Location(
            tenant_id=tenant_id,
            name=name,
            code=code,
            address=address,
            phone=phone,
            email=email,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Location | None:
        return (
            self.db.query(Location)
            .filter(Location.id == id)
            .first()
        )
