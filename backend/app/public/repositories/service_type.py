from app.db.repository import Repository
from app.public.models.service_type import ServiceType


class ServiceTypeRepository(Repository):
    def create(
        self,
        *,
        code: str,
        name: str,
    ) -> ServiceType:
        record = ServiceType(
            code=code,
            name=name,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: int,
    ) -> ServiceType | None:
        return (
            self.db.query(ServiceType)
            .filter(ServiceType.id == id)
            .first()
        )
