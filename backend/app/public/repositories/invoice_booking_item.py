from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.invoice_booking_item import InvoiceBookingItem


class InvoiceBookingItemRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        invoice_id: UUID,
        booking_id: UUID,
        line_description: str,
        amount_cents: int,
    ) -> InvoiceBookingItem:
        record = InvoiceBookingItem(
            invoice_id=invoice_id,
            booking_id=booking_id,
            line_description=line_description,
            amount_cents=amount_cents,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> InvoiceBookingItem | None:
        return (
            self.db.query(InvoiceBookingItem)
            .filter(InvoiceBookingItem.id == id)
            .first()
        )
