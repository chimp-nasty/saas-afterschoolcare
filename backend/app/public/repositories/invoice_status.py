from sqlalchemy.orm import Session

from app.public.models.invoice_status import InvoiceStatus


class InvoiceStatusRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        code: str,
        label: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> InvoiceStatus:
        record = InvoiceStatus(
            code=code,
            label=label,
            description=description,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: int,
    ) -> InvoiceStatus | None:
        return (
            self.db.query(InvoiceStatus)
            .filter(InvoiceStatus.id == id)
            .first()
        )
