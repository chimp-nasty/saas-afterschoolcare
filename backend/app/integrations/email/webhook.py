import json
import logging
import urllib.request

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmailStatusEnum as EmailStatus
from app.db.transaction import transactional
from app.errors.email import InvalidEmailWebhookError
from app.integrations.email import sns
from app.integrations.email.repository import EmailMessageRepository


logger = logging.getLogger("app.email")


# How far along an email is. A status only moves forward, so a late or
# repeated event can't undo a later one (a bounce isn't overwritten by a
# delivery that SES reported first, and so on).
_PROGRESS = {
    EmailStatus.QUEUED: 0,
    EmailStatus.SENT: 1,
    EmailStatus.FAILED: 2,
    EmailStatus.DELIVERED: 2,
    EmailStatus.BOUNCED: 3,
    EmailStatus.COMPLAINED: 4,
}


def _status_for(event: dict) -> EmailStatus | None:
    """The log status an SES event means, if any."""
    # Configuration set event publishing says eventType; identity
    # notifications say notificationType.
    kind = event.get("eventType") or event.get("notificationType")

    if kind == "Delivery":
        return EmailStatus.DELIVERED

    if kind == "Bounce":
        # A transient (soft) bounce may still be delivered later.
        bounce_type = (event.get("bounce") or {}).get("bounceType")
        return None if bounce_type == "Transient" else EmailStatus.BOUNCED

    if kind == "Complaint":
        return EmailStatus.COMPLAINED

    if kind in ("Reject", "Rendering Failure"):
        return EmailStatus.FAILED

    # Send, DeliveryDelay, and anything else: nothing to record.
    return None


class SesWebhookService:
    """
    What happened to our emails after SES accepted them: bounce, complaint
    and delivery events, published by the configuration sets to an SNS topic
    that posts here.

    Each event updates its email's status in the log, found by SES message
    id. The payload itself (it carries the full address and subject) is
    never stored or logged (docs/email-policy.md, section 6).
    """

    def __init__(
        self,
        *,
        db: Session,
        email_messages: EmailMessageRepository,
    ):
        self.db = db
        self.email_messages = email_messages

    def handle(
        self,
        *,
        payload: bytes,
    ) -> None:
        try:
            message = json.loads(payload)
            sns.verify(message, topic_arn=settings.SES_EVENTS_TOPIC_ARN)
        except (ValueError, sns.InvalidSnsMessage) as exc:
            raise InvalidEmailWebhookError(log_reason=f"ses webhook: {exc}") from exc

        message_type = message["Type"]

        if message_type == "SubscriptionConfirmation":
            self._confirm_subscription(subscribe_url=message.get("SubscribeURL", ""))

        elif message_type == "Notification":
            try:
                event = json.loads(message["Message"])
            except ValueError as exc:
                raise InvalidEmailWebhookError(log_reason="ses webhook: event isn't JSON") from exc

            self._record(event=event)

        else:
            logger.warning(
                "SES events topic unsubscribed us",
                extra={
                    "event": "ses_webhook_unsubscribed",
                    "result": "ignored",
                    "reason": message.get("TopicArn"),
                },
            )

    def _confirm_subscription(
        self,
        *,
        subscribe_url: str,
    ) -> None:
        """Confirm our topic's subscription (once, when it's set up)."""
        if not sns.is_sns_url(subscribe_url):
            raise InvalidEmailWebhookError(log_reason="ses webhook: subscribe URL not from SNS")

        with urllib.request.urlopen(subscribe_url, timeout=5):
            pass

        logger.info(
            "SES events subscription confirmed",
            extra={
                "event": "ses_webhook_subscribed",
                "result": "success",
                "reason": settings.SES_EVENTS_TOPIC_ARN,
            },
        )

    @transactional
    def _record(
        self,
        *,
        event: dict,
    ) -> None:
        status = _status_for(event)
        provider_message_id = (event.get("mail") or {}).get("messageId")

        if status is None or not provider_message_id:
            return

        # The log's only write path (schema/0005).
        self.email_messages.enable_writer()

        email = self.email_messages.get_by_provider_message_id(
            provider_message_id=provider_message_id,
        )

        # Not ours (e.g. another app on the account), or already further on.
        if not email or _PROGRESS[status] <= _PROGRESS[EmailStatus(email.status)]:
            return

        self.email_messages.update_status(message=email, status=status)

        log = logger.warning if status in (EmailStatus.BOUNCED, EmailStatus.COMPLAINED) else logger.info
        log(
            "Email status updated",
            extra={
                "event": f"email_{status.value}",
                "result": status.value,
                "reason": f"email_message_id={email.id}; type={getattr(email.email_type, 'value', email.email_type)}",
            },
        )
