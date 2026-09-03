from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.location_kiosk_device import LocationKioskDevice


class LocationKioskDeviceRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        location_id: UUID,
        name: str,
        setup_secret_hash: str | None = None,
        token_version: int = 1,
        is_active: bool = True,
    ) -> LocationKioskDevice:
        record = LocationKioskDevice(
            location_id=location_id,
            name=name,
            setup_secret_hash=setup_secret_hash,
            token_version=token_version,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> LocationKioskDevice | None:
        return (
            self.db.query(LocationKioskDevice)
            .filter(LocationKioskDevice.id == id)
            .first()
        )
