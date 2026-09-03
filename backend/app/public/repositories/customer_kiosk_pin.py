from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.customer_kiosk_pin import CustomerKioskPin


class CustomerKioskPinRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        pin_hash: str,
    ) -> CustomerKioskPin:
        record = CustomerKioskPin(
            user_id=user_id,
            pin_hash=pin_hash,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> CustomerKioskPin | None:
        return (
            self.db.query(CustomerKioskPin)
            .filter(CustomerKioskPin.id == id)
            .first()
        )
