from sqlalchemy.orm import Session

from app.public.models.service_type import ServiceType


class ServiceTypeRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        code: str,
        label: str,
        stripe_product_id: str | None = None,
        stripe_price_id: str | None = None,
        is_active: bool = True,
    ) -> ServiceType:
        record = ServiceType(
            code=code,
            label=label,
            stripe_product_id=stripe_product_id,
            stripe_price_id=stripe_price_id,
            is_active=is_active,
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
