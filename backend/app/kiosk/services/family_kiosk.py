import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.kiosk import (
    KioskLoginInvalidError,
    KioskLoginLockedError,
    KioskPinExpiredError,
    KioskSetupCodeInvalidError,
)
from app.integrations.email.messages import KioskPinEmail
from app.integrations.email.outbox import EmailOutbox
from app.kiosk.dependencies import KioskDevice, KioskSession
from app.kiosk.repositories.kiosk import KioskRepository
from app.kiosk.schemas.kiosk import (
    KioskBookingResponse,
    KioskInfoResponse,
    KioskLoginResponse,
    KioskServiceTodayResponse,
    KioskSessionResponse,
    KioskSignResponse,
    KioskTodayResponse,
)
from app.kiosk.tokens import issue_device_token, issue_session_token
from app.tenancy.repositories.location import LocationRepository


logger = logging.getLogger("app.kiosk")

_LOGIN_ERRORS = {
    "invalid": KioskLoginInvalidError,
    "locked": KioskLoginLockedError,
    "expired": KioskPinExpiredError,
}


class FamilyKioskService:
    """
    The family kiosk: pickup people signing their children in and out.
    The tablet has no user session; everything goes through the kiosk_*
    database functions (KioskRepository), which hold the rules: PIN checks
    and locks, the 30-day setup PIN limit, which bookings a person sees,
    and who may sign out (schema/0004).
    """

    def __init__(
        self,
        *,
        db: Session,
        kiosk_repository: KioskRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.kiosk_repository = kiosk_repository
        self.location_repository = location_repository
        self.emails = EmailOutbox(db)

    @transactional
    def pair(
        self,
        *,
        location_id: UUID,
        code: str,
    ) -> tuple[str, KioskInfoResponse]:
        """The device cookie's token, and what was paired."""
        row = self.kiosk_repository.pair(location_id=location_id, code=code)

        if not row:
            raise KioskSetupCodeInvalidError()

        logger.info(
            "Kiosk paired",
            extra={
                "event": "kiosk_paired",
                "result": "success",
                "reason": f"device_id={row.device_id}; kind={row.kind}",
            },
        )

        return (
            issue_device_token(
                device_id=row.device_id,
                location_id=location_id,
                kind=row.kind,
                token_version=row.token_version,
            ),
            self._describe(location_id=location_id, kind=row.kind),
        )

    def describe(
        self,
        *,
        device: KioskDevice,
    ) -> KioskInfoResponse:
        return self._describe(location_id=device.location_id, kind=device.kind)

    @transactional
    def login(
        self,
        *,
        device: KioskDevice,
        phone: str,
        pin: str,
    ) -> KioskLoginResponse:
        row = self.kiosk_repository.login(location_id=device.location_id, phone=phone, pin=pin)

        if row.result != "ok":
            logger.info(
                "Kiosk login refused",
                extra={
                    "event": "kiosk_login_refused",
                    "result": row.result,
                    "reason": f"device_id={device.device_id}",
                },
            )
            # Raised after the commit: a wrong PIN still counts.
            self.db.commit()
            raise _LOGIN_ERRORS[row.result]()

        return KioskLoginResponse(
            session=self._session(
                device=device,
                pickup_person_id=row.pickup_person_id,
                pin_change_required=row.pin_change_required,
            ),
            first_name=row.first_name,
            pin_change_required=row.pin_change_required,
        )

    @transactional
    def change_pin(
        self,
        *,
        session: KioskSession,
        new_pin: str,
    ) -> KioskSessionResponse:
        self.kiosk_repository.change_pin(
            location_id=session.device.location_id,
            pickup_person_id=session.subject_id,
            new_pin=new_pin,
        )

        logger.info(
            "Kiosk PIN changed",
            extra={
                "event": "kiosk_pin_changed",
                "result": "success",
                "reason": f"pickup_person_id={session.subject_id}",
            },
        )

        return self._session(device=session.device, pickup_person_id=session.subject_id)

    @transactional
    def forgot_pin(
        self,
        *,
        device: KioskDevice,
        phone: str,
    ) -> None:
        """
        Email a new PIN to the person with this mobile. The caller says the
        same thing whether or not anyone was found (or it was too soon).
        """
        row = self.kiosk_repository.forgot_pin(location_id=device.location_id, phone=phone)

        if not row:
            return

        self.emails.queue(KioskPinEmail(
            location_id=device.location_id,
            pickup_person_id=row.pickup_person_id,
            to_email=row.email,
            first_name=row.first_name,
            pin=row.pin,
        ))

        logger.info(
            "Kiosk PIN reset",
            extra={
                "event": "kiosk_pin_reset",
                "result": "success",
                "reason": f"pickup_person_id={row.pickup_person_id}",
            },
        )

    def today(
        self,
        *,
        session: KioskSession,
    ) -> KioskTodayResponse:
        rows = self.kiosk_repository.family_today(
            location_id=session.device.location_id,
            pickup_person_id=session.subject_id,
        )

        return KioskTodayResponse(
            session=self._session(device=session.device, pickup_person_id=session.subject_id),
            bookings=[KioskBookingResponse.model_validate(row, from_attributes=True) for row in rows],
        )

    @transactional
    def sign(
        self,
        *,
        session: KioskSession,
        booking_id: UUID,
        action: str,
    ) -> KioskSignResponse:
        row = self.kiosk_repository.sign(
            location_id=session.device.location_id,
            device_id=session.device.device_id,
            pickup_person_id=session.subject_id,
            booking_id=booking_id,
            action=action,
        )

        logger.info(
            "Kiosk sign",
            extra={
                "event": f"kiosk_sign_{action}",
                "result": "success",
                "reason": f"booking_id={booking_id}; pickup_person_id={session.subject_id}",
            },
        )

        return KioskSignResponse(
            session=self._session(device=session.device, pickup_person_id=session.subject_id),
            booking_id=booking_id,
            signed_in_at=row.signed_in_at,
            signed_out_at=row.signed_out_at,
        )

    def _session(
        self,
        *,
        device: KioskDevice,
        pickup_person_id: UUID,
        pin_change_required: bool = False,
    ) -> KioskSessionResponse:
        token, expires_at = issue_session_token(
            kind="family",
            device_id=device.device_id,
            location_id=device.location_id,
            subject_id=pickup_person_id,
            pin_change_required=pin_change_required,
        )

        return KioskSessionResponse(token=token, expires_at=expires_at)

    def _describe(
        self,
        *,
        location_id: UUID,
        kind: str,
    ) -> KioskInfoResponse:
        location = self.location_repository.get_by_id(id=location_id)

        return KioskInfoResponse(
            kind=getattr(kind, "value", kind),
            location_name=location.name,
            sessions_today=[
                KioskServiceTodayResponse.model_validate(row, from_attributes=True)
                for row in self.kiosk_repository.location_today(location_id=location_id)
            ],
        )
