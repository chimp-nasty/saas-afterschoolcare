from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.kiosk.dependencies import KioskDevice
from app.kiosk.repositories.staff_kiosk import StaffKioskRepository
from app.kiosk.schemas.kiosk import KioskInfoResponse
from app.kiosk.schemas.staff_kiosk import (
    StaffKioskMemberResponse,
    StaffKioskVerifyResponse,
)
from app.public.schemas.attendance import RunSheetEntryResponse, RunSheetResponse, RunSheetSessionResponse
from app.public.services.attendance import location_today
from app.tenancy.repositories.location import LocationRepository


class StaffKioskService:
    """
    What the staff kiosk shows before anyone enters a PIN: what it is, the
    staff to choose from, and the run sheet without personal details
    (docs/portals.md, section 1.3). Everything a staff member does there
    (attendance, ID checks, shifts, reading families' details) goes through
    the normal services, as them, on the kiosk channel.
    """

    def __init__(
        self,
        *,
        db: Session,
        staff_kiosk_repository: StaffKioskRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.staff_kiosk_repository = staff_kiosk_repository
        self.location_repository = location_repository

    def describe(
        self,
        *,
        device: KioskDevice,
    ) -> KioskInfoResponse:
        location = self.location_repository.get_by_id(id=device.location_id)

        return KioskInfoResponse(kind="staff", location_name=location.name)

    def staff(
        self,
        *,
        device: KioskDevice,
    ) -> list[StaffKioskMemberResponse]:
        rows = self.staff_kiosk_repository.staff(location_id=device.location_id, device_id=device.device_id)

        return [StaffKioskMemberResponse.model_validate(row, from_attributes=True) for row in rows]

    def board(
        self,
        *,
        device: KioskDevice,
        on: date | None,
    ) -> RunSheetResponse:
        on = on or location_today(self.location_repository.get_by_id(id=device.location_id))
        where = {"location_id": device.location_id, "device_id": device.device_id, "on": on}
        sessions = self.staff_kiosk_repository.sessions(**where)
        rows = self.staff_kiosk_repository.board(**where)

        return RunSheetResponse(
            date=on,
            sessions=[RunSheetSessionResponse.model_validate(row, from_attributes=True) for row in sessions],
            entries=[RunSheetEntryResponse.model_validate(row, from_attributes=True) for row in rows],
        )

    def verify(
        self,
        *,
        device: KioskDevice,
        user_id: UUID,
    ) -> StaffKioskVerifyResponse:
        [member] = [m for m in self.staff(device=device) if m.user_id == user_id]

        return StaffKioskVerifyResponse(user_id=user_id, first_name=member.first_name)
