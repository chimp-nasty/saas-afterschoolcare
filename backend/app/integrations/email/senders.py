"""
Where a rendered email goes: Amazon SES, or (dev and tests) the app log.
EmailClient picks one from EMAIL_PROVIDER; nothing else talks to SES.
"""

import logging
import uuid
from dataclasses import dataclass
from email.utils import formataddr

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.integrations.email.renderer import RenderedEmail


logger = logging.getLogger("app.email")


@dataclass(frozen=True)
class OutgoingEmail:
    to_email: str
    from_name: str
    reply_to: str | None
    rendered: RenderedEmail
    requires_tls: bool
    # The SES tenant (the tenant's code) and the tags on the message.
    tenant_name: str
    tags: dict[str, str]


@dataclass(frozen=True)
class SendResult:
    # The provider's message id when it accepted the email.
    message_id: str | None = None
    # A code only, never the provider's message (it can quote the address).
    error_code: str | None = None


class LogSender:
    """
    Writes emails to the app log instead of sending them. The body (which
    can hold a reset link or PIN) is only logged in dev, like the PIN stub
    before it; it must never reach a production log.
    """

    def send(self, email: OutgoingEmail) -> SendResult:
        logger.info(
            "Email (not sent: EMAIL_PROVIDER=log)",
            extra={
                "event": "email_logged",
                "result": "stubbed",
                "reason": (
                    f"subject={email.rendered.subject}; tls={email.requires_tls}"
                    + (f"\n{email.rendered.text}" if settings.APP_ENV == "dev" else "")
                ),
            },
        )

        return SendResult(message_id=f"log-{uuid.uuid4()}")


class SesSender:
    """
    Amazon SES v2 in Sydney, as finished content (no SES-stored templates).
    From the platform's address under the centre's name, replies to the
    centre. Configuration sets carry the event publishing (bounces,
    complaints, deliveries; no open or click tracking) and, for emails with
    a secret, the TLS requirement.
    """

    def __init__(self):
        credentials = {}

        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            credentials = {
                "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            }

        self._client = boto3.client("sesv2", region_name=settings.SES_REGION, **credentials)

    def send(self, email: OutgoingEmail) -> SendResult:
        configuration_set = (
            settings.SES_TLS_CONFIGURATION_SET
            if email.requires_tls
            else settings.SES_CONFIGURATION_SET
        )

        # An email with a secret never goes without its TLS configuration set.
        if email.requires_tls and not configuration_set:
            return SendResult(error_code="TlsConfigurationSetMissing")

        request = {
            "FromEmailAddress": formataddr((email.from_name, settings.SES_FROM_ADDRESS), charset="utf-8"),
            "Destination": {"ToAddresses": [email.to_email]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": email.rendered.subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": email.rendered.text, "Charset": "UTF-8"},
                        "Html": {"Data": email.rendered.html, "Charset": "UTF-8"},
                    },
                }
            },
            "EmailTags": [{"Name": name, "Value": value} for name, value in email.tags.items()],
        }

        if email.reply_to:
            request["ReplyToAddresses"] = [email.reply_to]

        if configuration_set:
            request["ConfigurationSetName"] = configuration_set

        if settings.SES_USE_TENANTS:
            request["TenantName"] = email.tenant_name

        try:
            response = self._client.send_email(**request)
        except ClientError as exc:
            return SendResult(error_code=exc.response.get("Error", {}).get("Code", "ClientError"))
        except BotoCoreError as exc:
            return SendResult(error_code=type(exc).__name__)

        return SendResult(message_id=response["MessageId"])
