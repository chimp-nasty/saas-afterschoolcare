import logging

from app.core.config import settings


logger = logging.getLogger("app.email")


class EmailClient:
    """
    Sends the app's emails. A stub for now: no email provider is integrated
    yet, so messages are logged instead of sent. Swap the bodies for a real
    provider later; callers don't change.

    A kiosk PIN is only ever written to the log in dev, so the kiosk can be
    tried before real email exists. It must never reach a production log.
    """

    def send_kiosk_pin(
        self,
        *,
        to_email: str,
        first_name: str,
        pin: str,
    ) -> None:
        logger.info(
            "Kiosk PIN email (not sent: email is stubbed)",
            extra={
                "event": "email_kiosk_pin",
                "result": "stubbed",
                "reason": (
                    f"to={to_email}; first_name={first_name}"
                    + (f"; pin={pin}" if settings.APP_ENV == "dev" else "")
                ),
            },
        )
