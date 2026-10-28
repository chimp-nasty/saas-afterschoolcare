import logging
from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.email.catalogue import CATALOGUE
from app.integrations.email.links import Links
from app.integrations.email.masking import mask_email
from app.integrations.email.messages import EmailMessage
from app.integrations.email.renderer import Centre, Override, render
from app.integrations.email.repository import EmailMessageRepository
from app.integrations.email.senders import (
    LogSender,
    OutgoingEmail,
    SendResult,
    SesSender,
)


logger = logging.getLogger("app.email")


def _sender():
    return SesSender() if settings.EMAIL_PROVIDER == "ses" else LogSender()


def delivery_address(to_email: str) -> str:
    """
    Where an email actually goes: SES's mailbox simulator for a test
    address (EMAIL_SIMULATOR_DOMAINS, deployed dev), else the recipient.
    """
    domain = to_email.rsplit("@", 1)[-1].lower()

    if domain in {d.lower() for d in settings.EMAIL_SIMULATOR_DOMAINS}:
        return settings.EMAIL_SIMULATOR_ADDRESS

    return to_email


class EmailClient:
    """
    Sends the app's emails: the only way out (docs/email-policy.md). Each
    send(message) (app/integrations/email/messages.py):

    1. logs a row in email_messages (masked address, no body)
    2. renders our wording, or the tenant's, as the centre
    3. sends it (SES, or the app log in dev; a test address goes to SES's
       mailbox simulator instead, delivery_address)
    4. records the outcome on the row

    The log is written in its own short transactions (app.email_writer),
    apart from the caller's session, and no transaction is open while
    sending. A send never raises: the action that triggered it has already
    happened, so a failure is logged and the row marked failed.

    Services don't call it: they queue messages on EmailOutbox, which sends
    them here once the transaction commits.
    """

    def __init__(
        self,
        *,
        sender=None,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self._sender = sender or _sender()
        self._session_factory = session_factory

    def send(self, message: EmailMessage | OutgoingEmail) -> UUID | None:
        """
        Log, render, send and record one email. Returns its log row's id.
        An OutgoingEmail is already finished and isn't a business's, so it
        has no catalogue entry or log row: the platform's own notices to
        itself (docs/platform-site.md).
        """
        if isinstance(message, OutgoingEmail):
            self._send_finished(message)
            return None

        email_type = message.email_type
        definition = CATALOGUE[email_type]
        location_id = message.location_id

        try:
            with self._session_factory() as db:
                repository = EmailMessageRepository(db=db)
                repository.enable_writer()

                sender = repository.get_sender(location_id=location_id)
                row = repository.get_override(tenant_id=sender.tenant_id, email_type=email_type)

                # Copied out now: ORM objects can't be read once the
                # session has committed and closed.
                override = Override(
                    subject=row.subject,
                    heading=row.heading,
                    body=row.body,
                    sign_off=row.sign_off,
                ) if row else None

                message_id = repository.create(
                    tenant_id=sender.tenant_id,
                    location_id=location_id,
                    email_type=email_type,
                    recipient_masked=mask_email(message.to_email),
                    **message.recipient(),
                ).id

                db.commit()
        except Exception as exc:
            # Nothing was logged, so this is the only trace.
            logger.error(
                "Email not logged or sent",
                extra={
                    "event": "email_not_logged",
                    "result": "failed",
                    "reason": f"type={email_type.value}; location_id={location_id}; {type(exc).__name__}",
                },
            )
            return None

        centre = Centre(
            name=sender.location_name or sender.tenant_name,
            email=sender.location_email or sender.tenant_email,
            phone=sender.location_phone,
            primary_color=sender.primary_color,
        )

        links = Links(
            tenant_code=sender.tenant_code,
            custom_domain=sender.custom_domain,
            location_code=sender.location_code,
        )

        try:
            rendered = render(
                definition,
                centre=centre,
                values=message.values(),
                block=message.block(links),
                override=override,
            )

            result = self._sender.send(
                OutgoingEmail(
                    to_email=delivery_address(message.to_email),
                    from_name=centre.name,
                    reply_to=centre.email,
                    rendered=rendered,
                    requires_tls=definition.requires_tls,
                    tenant_name=sender.tenant_code,
                    tags={
                        "tenant_id": str(sender.tenant_id),
                        "location_id": str(location_id),
                        "email_type": email_type.value,
                    },
                )
            )
        except Exception as exc:
            result = SendResult(error_code=type(exc).__name__)

        self._record(message_id=message_id, email_type=email_type, result=result)

        return message_id

    def _send_finished(self, email: OutgoingEmail) -> None:
        try:
            result = self._sender.send(replace(email, to_email=delivery_address(email.to_email)))
        except Exception as exc:
            result = SendResult(error_code=type(exc).__name__)

        logger.log(
            logging.ERROR if result.error_code else logging.INFO,
            "Platform email sent" if not result.error_code else "Platform email not sent",
            extra={
                "event": "platform_email",
                "result": "failed" if result.error_code else "success",
                "reason": result.error_code or f"type={email.tags.get('email_type', '-')}",
            },
        )

    def _record(
        self,
        *,
        message_id: UUID,
        email_type: EmailType,
        result: SendResult,
    ) -> None:
        try:
            with self._session_factory() as db:
                repository = EmailMessageRepository(db=db)
                repository.enable_writer()

                repository.record_result(
                    message=repository.get_by_id(id=message_id),
                    provider_message_id=result.message_id,
                    error_code=result.error_code,
                )

                db.commit()
        except Exception as exc:
            logger.error(
                "Email outcome not recorded",
                extra={
                    "event": "email_not_recorded",
                    "result": "failed",
                    "reason": f"email_message_id={message_id}; {type(exc).__name__}",
                },
            )
            return

        if result.error_code:
            logger.warning(
                "Email not sent",
                extra={
                    "event": "email_failed",
                    "result": "failed",
                    "reason": f"email_message_id={message_id}; type={email_type.value}; error={result.error_code}",
                },
            )
        else:
            logger.info(
                "Email sent",
                extra={
                    "event": "email_sent",
                    "result": "success",
                    "reason": f"email_message_id={message_id}; type={email_type.value}",
                },
            )
