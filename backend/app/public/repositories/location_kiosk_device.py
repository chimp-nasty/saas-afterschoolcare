from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from app.db.repository import Repository
from app.db.models import LocationKioskDevice


class LocationKioskDeviceRepository(Repository):
    """A location's kiosk tablets, as admins manage them (RLS: staff read, admins write)."""

    def create(
        self,
        *,
        location_id: UUID,
        kind: str,
        name: str,
        setup_secret_hash: str,
        setup_code_expires_at: datetime,
    ) -> LocationKioskDevice:
        record = LocationKioskDevice(
            location_id=location_id,
            kind=kind,
            name=name,
            setup_secret_hash=setup_secret_hash,
            setup_code_expires_at=setup_code_expires_at,
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

    def list_for_location(
        self,
        *,
        location_id: UUID,
    ) -> list[LocationKioskDevice]:
        """Active ones first, newest first."""
        return (
            self.db.query(LocationKioskDevice)
            .filter(LocationKioskDevice.location_id == location_id)
            .order_by(
                LocationKioskDevice.is_active.desc(),
                LocationKioskDevice.created_at.desc(),
            )
            .all()
        )

    def new_setup_code(
        self,
        *,
        device: LocationKioskDevice,
        setup_secret_hash: str,
        setup_code_expires_at: datetime,
    ) -> LocationKioskDevice:
        """
        Ready to pair again: the tablet holding the old cookie stops working
        (token_version + 1) until a tablet is paired with the new code.
        """
        device.setup_secret_hash = setup_secret_hash
        device.setup_code_expires_at = setup_code_expires_at
        device.token_version = device.token_version + 1
        device.paired_at = None

        self.db.flush()

        return device

    def revoke(
        self,
        *,
        device: LocationKioskDevice,
    ) -> LocationKioskDevice:
        device.is_active = False
        device.setup_secret_hash = None
        device.setup_code_expires_at = None

        self.db.flush()

        return device


    def enforces_service_times(
        self,
        *,
        location_id: UUID,
    ) -> bool:
        return self.db.execute(
            text("SELECT kiosk_enforce_service_times FROM tenancy.locations WHERE id = :location_id"),
            {"location_id": location_id},
        ).scalar_one()

    def set_enforce_service_times(
        self,
        *,
        location_id: UUID,
        enabled: bool,
    ) -> None:
        """public.set_kiosk_enforce_service_times: the location's admins only."""
        self.db.execute(
            text("SELECT public.set_kiosk_enforce_service_times(:location_id, :enabled)"),
            {"location_id": location_id, "enabled": enabled},
        )
