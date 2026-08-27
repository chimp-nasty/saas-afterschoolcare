from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.tenancy.models.tenant import Tenant


class TenantRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        name: str,
        code: str,
        terms_accepted_at: datetime,
        email: str | None = None,
        terms_version: str = "v1",
        is_active: bool = True,
    ) -> Tenant:
        record = Tenant(
            name=name,
            code=code,
            terms_accepted_at=terms_accepted_at,
            email=email,
            terms_version=terms_version,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Tenant | None:
        return (
            self.db.query(Tenant)
            .filter(Tenant.id == id)
            .first()
        )

    def get_by_code(
        self,
        *,
        code: str
    ) -> Tenant | None:
        return (
            self.db.query(Tenant)
            .filter(Tenant.code == code)
            .first()
        )
        
    def get_by_custom_domain(
        self,
        *,
        custom_domain: str
    ) -> Tenant | None:
        return (
            self.db.query(Tenant)
            .filter(Tenant.custom_domain == custom_domain)
            .first()
        )