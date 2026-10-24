from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.engine import Row

from app.db.repository import Repository
from app.db.models import (
    EmailMessage,
    EmailStatusEnum,
    EmailTemplateOverride,
    Location,
    Tenant,
    TenantBranding,
)


class EmailMessageRepository(Repository):
    """
    The email log, and what's needed to send as a centre. Used only by
    EmailClient, in its own transactions with app.email_writer on: the log's
    only write path (schema/0005).
    """

    def enable_writer(self) -> None:
        # Transaction-local, like the RLS settings: set again after a commit.
        self.db.execute(select(func.set_config("app.email_writer", "on", True)))

    def get_sender(
        self,
        *,
        location_id: UUID,
    ) -> Row | None:
        """The location, its tenant and the business's brand colour."""
        return (
            self.db.query(
                Location.code.label("location_code"),
                Location.name.label("location_name"),
                Location.email.label("location_email"),
                Location.phone.label("location_phone"),
                Tenant.id.label("tenant_id"),
                Tenant.code.label("tenant_code"),
                Tenant.name.label("tenant_name"),
                Tenant.email.label("tenant_email"),
                Tenant.custom_domain,
                TenantBranding.primary_color,
            )
            .join(Tenant, Tenant.id == Location.tenant_id)
            .outerjoin(TenantBranding, TenantBranding.tenant_id == Location.tenant_id)
            .filter(Location.id == location_id)
            .first()
        )

    def get_override(
        self,
        *,
        tenant_id: UUID,
        email_type: str,
    ) -> EmailTemplateOverride | None:
        return (
            self.db.query(EmailTemplateOverride)
            .filter(
                EmailTemplateOverride.tenant_id == tenant_id,
                EmailTemplateOverride.email_type == email_type,
            )
            .first()
        )

    def create(
        self,
        *,
        tenant_id: UUID,
        location_id: UUID,
        email_type: str,
        recipient_masked: str,
        recipient_user_id: UUID | None = None,
        recipient_pickup_person_id: UUID | None = None,
    ) -> EmailMessage:
        # trg_email_messages_tenant sets tenant_id from the location anyway,
        # so the two can't disagree.
        record = EmailMessage(
            location_id=location_id,
            tenant_id=tenant_id,
            email_type=email_type,
            recipient_masked=recipient_masked,
            recipient_user_id=recipient_user_id,
            recipient_pickup_person_id=recipient_pickup_person_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> EmailMessage | None:
        return (
            self.db.query(EmailMessage)
            .filter(EmailMessage.id == id)
            .first()
        )

    def record_result(
        self,
        *,
        message: EmailMessage,
        provider_message_id: str | None,
        error_code: str | None,
    ) -> EmailMessage:
        now = datetime.now(timezone.utc)

        if provider_message_id:
            message.status = EmailStatusEnum.SENT
            message.provider_message_id = provider_message_id
            message.sent_at = now
        else:
            message.status = EmailStatusEnum.FAILED
            message.error_code = (error_code or "Unknown")[:100]

        message.status_updated_at = now

        self.db.flush()

        return message

    def get_by_provider_message_id(
        self,
        *,
        provider_message_id: str,
    ) -> EmailMessage | None:
        return (
            self.db.query(EmailMessage)
            .filter(EmailMessage.provider_message_id == provider_message_id)
            .first()
        )

    def update_status(
        self,
        *,
        message: EmailMessage,
        status: EmailStatusEnum,
    ) -> EmailMessage:
        message.status = status
        message.status_updated_at = datetime.now(timezone.utc)

        self.db.flush()

        return message
