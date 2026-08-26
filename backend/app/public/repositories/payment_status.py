from sqlalchemy.orm import Session

from app.public.models.payment_status import PaymentStatus


class PaymentStatusRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        code: str,
        label: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> PaymentStatus:
        record = PaymentStatus(
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
    ) -> PaymentStatus | None:
        return (
            self.db.query(PaymentStatus)
            .filter(PaymentStatus.id == id)
            .first()
        )
