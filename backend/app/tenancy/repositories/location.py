from uuid import UUID

from app.db.repository import Repository
from app.tenancy.models.location import Location


class LocationRepository(Repository):
    def create(
        self,
        *,
        tenant_id: UUID,
        name: str | None = None,
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

    def get_by_tenant_and_code(
        self,
        *,
        tenant_id: UUID,
        code: str
    ) -> Location:
        return (
            self.db.query(Location)
            .filter(
                Location.tenant_id == tenant_id,
                Location.code == code,
            )
            .first()
        )