import logging
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.db.transaction import transactional
from app.errors.payments import PaymentProviderError
from app.integrations.payments.stripe.settlement import PaymentSettlementService
from app.public.repositories.payment_attempt import PaymentAttemptRepository


logger = logging.getLogger("app.payments")


class PaymentCheckService:
    """
    The scheduled payment check (docs/payment-confirmation.md): Cloud
    Scheduler calls it every 5 minutes. Every pending payment attempt is
    checked with Stripe and settled if Stripe has finished with it (paid or
    expired), so a missed webhook can't leave a family's booking stuck, even
    if they closed the tab before the success page. Well inside the 60
    minute booking hold, so a paid booking keeps its place.

    Server code with no user: the list comes from public.pending_checkouts
    (the payment_check channel), then each attempt is settled in its own
    transaction acting as its family, as the webhook does.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        payment_attempt_repository: PaymentAttemptRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.payment_attempt_repository = payment_attempt_repository
        self.settlement = PaymentSettlementService.on(db)

    def check_all(self) -> int:
        """Returns how many attempts were checked."""
        pending = self._pending()

        for row in pending:
            # One payment Stripe can't tell us about doesn't hold up the
            # others; it's tried again next time.
            try:
                self._check(
                    payment_attempt_id=row.payment_attempt_id,
                    user_id=row.user_id,
                    location_id=row.location_id,
                )
            except PaymentProviderError as exc:
                logger.warning(
                    "Payment check couldn't reach Stripe for an attempt",
                    extra={
                        "event": "payment_check",
                        "result": "failed",
                        "reason": f"payment_attempt_id={row.payment_attempt_id}; {exc.log_reason}",
                    },
                )
            except Exception:
                logger.exception(
                    "Payment check failed for an attempt",
                    extra={
                        "event": "payment_check",
                        "result": "failed",
                        "reason": f"payment_attempt_id={row.payment_attempt_id}",
                    },
                )

        return len(pending)

    @transactional
    def _pending(self) -> list[Row]:
        self.rls_context.set_payment_check_channel()

        return self.payment_attempt_repository.list_pending_checkouts()

    @transactional
    def _check(
        self,
        *,
        payment_attempt_id: UUID,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        attempt = self.settlement.lock_pending(
            payment_attempt_id=payment_attempt_id,
            user_id=user_id,
            location_id=location_id,
        )

        if attempt:
            self.settlement.reconcile(attempt=attempt, settle_expired=True)
