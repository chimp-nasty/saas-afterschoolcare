from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row

from app.db.repository import Repository


class KioskRepository(Repository):
    """
    The kiosk's only way into the database: the kiosk_* functions
    (schema/0004). A tablet has no user session, so RLS shows it nothing;
    each function does one thing for one location and person.
    """

    def pair(
        self,
        *,
        location_id: UUID,
        code: str,
    ) -> Row | None:
        """(device_id, kind, token_version), or None for a bad code."""
        return self.db.execute(
            text("SELECT * FROM public.kiosk_pair(:location_id, :code)"),
            {"location_id": location_id, "code": code},
        ).first()

    def device(
        self,
        *,
        device_id: UUID,
        token_version: int,
    ) -> Row | None:
        """(location_id, kind) of a current, paired device; records its use."""
        return self.db.execute(
            text("SELECT * FROM public.kiosk_device(:device_id, :token_version)"),
            {"device_id": device_id, "token_version": token_version},
        ).first()

    def login(
        self,
        *,
        location_id: UUID,
        phone: str,
        pin: str,
    ) -> Row:
        """(result, pickup_person_id, first_name, pin_change_required)."""
        return self.db.execute(
            text("SELECT * FROM public.kiosk_login(:location_id, :phone, :pin)"),
            {"location_id": location_id, "phone": phone, "pin": pin},
        ).one()

    def change_pin(
        self,
        *,
        location_id: UUID,
        pickup_person_id: UUID,
        new_pin: str,
    ) -> None:
        self.db.execute(
            text("SELECT public.kiosk_change_pin(:location_id, :person_id, :new_pin)"),
            {"location_id": location_id, "person_id": pickup_person_id, "new_pin": new_pin},
        )

    def forgot_pin(
        self,
        *,
        location_id: UUID,
        phone: str,
    ) -> Row | None:
        """(pickup_person_id, email, first_name, pin) to email, or None."""
        return self.db.execute(
            text("SELECT * FROM public.kiosk_forgot_pin(:location_id, :phone)"),
            {"location_id": location_id, "phone": phone},
        ).first()

    def location_today(
        self,
        *,
        location_id: UUID,
    ) -> list[Row]:
        """The centre's own sessions today, for the welcome screen (no family details)."""
        return self.db.execute(
            text("SELECT * FROM public.kiosk_location_today(:location_id)"),
            {"location_id": location_id},
        ).all()

    def family_today(
        self,
        *,
        location_id: UUID,
        pickup_person_id: UUID,
    ) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.kiosk_family_today(:location_id, :person_id)"),
            {"location_id": location_id, "person_id": pickup_person_id},
        ).all()

    def sign(
        self,
        *,
        location_id: UUID,
        device_id: UUID,
        pickup_person_id: UUID,
        booking_id: UUID,
        action: str,
    ) -> Row:
        """(signed_in_at, signed_out_at) after signing."""
        return self.db.execute(
            text(
                "SELECT * FROM public.kiosk_sign("
                ":location_id, :device_id, :person_id, :booking_id, :action)"
            ),
            {
                "location_id": location_id,
                "device_id": device_id,
                "person_id": pickup_person_id,
                "booking_id": booking_id,
                "action": action,
            },
        ).one()
