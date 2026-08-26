from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.user_kiosk_pin import UserKioskPin


class UserKioskPinRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        pin_hash: str,
        last_used_at: datetime | None = None,
    ) -> UserKioskPin:
        record = UserKioskPin(
            user_id=user_id,
            pin_hash=pin_hash,
            last_used_at=last_used_at,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> UserKioskPin | None:
        return (
            self.db.query(UserKioskPin)
            .filter(UserKioskPin.id == id)
            .first()
        )
