from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.invoice import Invoice


class InvoiceRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        parent_id: UUID,
        billing_period_start: date,
        billing_period_end: date,
        status_id: int,
        subtotal_cents: int,
        total_cents: int,
        currency: str,
        discount_cents: int = 0,
        issued_at: datetime | None = None,
        due_at: datetime | None = None,
        paid_at: datetime | None = None,
        stripe_customer_id: str | None = None,
        stripe_invoice_id: str | None = None,
        stripe_receipt_url: str | None = None,
        stripe_payment_intent_id: str | None = None,
        stripe_checkout_session_id: str | None = None,
    ) -> Invoice:
        record = Invoice(
            parent_id=parent_id,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            status_id=status_id,
            subtotal_cents=subtotal_cents,
            total_cents=total_cents,
            currency=currency,
            discount_cents=discount_cents,
            issued_at=issued_at,
            due_at=due_at,
            paid_at=paid_at,
            stripe_customer_id=stripe_customer_id,
            stripe_invoice_id=stripe_invoice_id,
            stripe_receipt_url=stripe_receipt_url,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_checkout_session_id=stripe_checkout_session_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Invoice | None:
        return (
            self.db.query(Invoice)
            .filter(Invoice.id == id)
            .first()
        )
