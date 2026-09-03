from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.refund import Refund


class RefundRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        booking_id: UUID,
        location_id: UUID,
        user_id: UUID,
        requested_by_user_id: UUID,
        reason: str | None = None,
        stripe_refund_id: str | None = None,
        failed_at=None,
        failure_reason: str | None = None,
        processed_at=None,
    ) -> Refund:
        record = Refund(
            booking_id=booking_id,
            location_id=location_id,
            user_id=user_id,
            requested_by_user_id=requested_by_user_id,
            reason=reason,
            stripe_refund_id=stripe_refund_id,
            failed_at=failed_at,
            failure_reason=failure_reason,
            processed_at=processed_at,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> Refund | None:
        return (
            self.db.query(Refund)
            .filter(Refund.id == id)
            .first()
        )
