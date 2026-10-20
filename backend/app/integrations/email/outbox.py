"""
Emails wait for their transaction: a service queues a message where the
change happens, and it's sent only if that transaction commits.

    self.emails = EmailOutbox(db)            # in the service's __init__
    self.emails.queue(ChildApprovedEmail(...))   # inside the @transactional method

The listeners below hang off every SQLAlchemy session, so the rule holds
however the transaction ends: @transactional, services that commit several
times (refunds), webhooks. A rollback drops what was queued, so nobody is
emailed about a change that didn't happen.

Sending happens inside commit(), before the response. EmailClient uses its
own sessions (never the committing one) and never raises, so an email can't
disturb the commit or the request.
"""

import logging

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.integrations.email.client import EmailClient
from app.integrations.email.messages import EmailMessage


logger = logging.getLogger("app.email")

_KEY = "email_outbox"


class EmailOutbox:
    """The emails waiting for the current transaction on `db` to commit."""

    def __init__(self, db: Session):
        self.db = db

    def queue(self, message: EmailMessage) -> None:
        self.db.info.setdefault(_KEY, []).append(message)


@event.listens_for(Session, "after_commit")
def _send_queued(session: Session) -> None:
    messages = session.info.pop(_KEY, None)

    if not messages:
        return

    client = EmailClient()

    for message in messages:
        try:
            client.send(message)
        except Exception as exc:
            # send() doesn't raise; this is a last guard for the commit.
            logger.error(
                "Queued email not sent",
                extra={
                    "event": "email_outbox_failed",
                    "result": "failed",
                    "reason": f"type={message.email_type.value}; {type(exc).__name__}",
                },
            )


@event.listens_for(Session, "after_rollback")
def _drop_queued(session: Session) -> None:
    session.info.pop(_KEY, None)
