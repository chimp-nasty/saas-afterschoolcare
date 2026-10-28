import logging
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.auth.repositories.user import UserRepository
from app.db.transaction import transactional
from app.errors.payments import InvalidWebhookError
from app.integrations.email.messages import RefundConfirmationEmail, short_reference
from app.integrations.email.outbox import EmailOutbox
from app.integrations.payments.stripe.client import StripeClient
from app.integrations.payments.stripe.settlement import PaymentSettlementService
from app.public.repositories.booking import BookingRepository
from app.public.repositories.payment_attempt import PaymentAttemptRepository
from app.public.repositories.refund import RefundRepository
from app.public.schemas.enums import RefundStatus
from app.tenancy.repositories.stripe_account import TenantStripeAccountRepository


logger = logging.getLogger("app.payments")


class StripeWebhookService:
    """
    Stripe's events. Payments are settled through PaymentSettlementService,
    which is also used when Stripe is asked directly in case a webhook was
    missed (the success page, cancelling, continuing to payment, the
    scheduled payment check; docs/payment-confirmation.md).

    Two endpoints: the platform's, and Stripe Connect's (`connect`) for
    events on tenants' connected accounts, where their checkouts and
    refunds happen (direct charges), plus account.updated and
    account.application.deauthorized. A payment or refund is only settled
    by an event from the account it was made in.
    """

    def __init__(
        self,
        *,
        db: Session,
        rls_context: RlsContextRepository,
        payment_attempt_repository: PaymentAttemptRepository,
        booking_repository: BookingRepository,
        refund_repository: RefundRepository,
        user_repository: UserRepository,
        stripe_account_repository: TenantStripeAccountRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.payment_attempt_repository = payment_attempt_repository
        self.booking_repository = booking_repository
        self.refund_repository = refund_repository
        self.user_repository = user_repository
        self.stripe_account_repository = stripe_account_repository
        self.stripe = StripeClient()
        self.emails = EmailOutbox(db)
        self.settlement = PaymentSettlementService(
            db=db,
            rls_context=rls_context,
            payment_attempt_repository=payment_attempt_repository,
            booking_repository=booking_repository,
            user_repository=user_repository,
        )

    def handle(
        self,
        *,
        payload: bytes,
        signature: str | None,
        connect: bool = False,
    ) -> None:
        try:
            event = self.stripe.construct_webhook_event(
                payload=payload,
                signature=signature or "",
                connect=connect,
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise InvalidWebhookError(log_reason=str(exc)) from exc

        event_type = event["type"]
        session = event["data"]["object"]
        # The connected account the event happened in (None: the platform's).
        account_id = event.get("account") if connect else None

        if event_type == "account.updated" and connect:
            self._sync_account(stripe_account=session)
            return

        if event_type == "account.application.deauthorized" and connect:
            self._revoke_account(account_id=account_id)
            return

        if event_type == "checkout.session.completed":
            # Card payments are "paid" here; delayed methods (e.g. bank
            # debits) settle later via the async_payment_* events.
            if session["payment_status"] == "paid":
                self._settle(session=session, succeeded=True, account_id=account_id)

        elif event_type == "checkout.session.async_payment_succeeded":
            self._settle(session=session, succeeded=True, account_id=account_id)

        elif event_type in (
            "checkout.session.expired",
            "checkout.session.async_payment_failed",
        ):
            self._settle(session=session, succeeded=False, account_id=account_id)

        # A Refund object; its status says how far it's got.
        elif event_type in (
            "refund.created",
            "refund.updated",
            "refund.failed",
        ):
            self._settle_refund(stripe_refund=session, account_id=account_id)

        # Anything else is acknowledged and ignored.

    @transactional
    def _sync_account(self, *, stripe_account) -> None:
        """Keep a tenant's account flags as Stripe reports them."""
        known = self.stripe_account_repository.sync(
            stripe_account_id=stripe_account["id"],
            charges_enabled=bool(stripe_account.get("charges_enabled")),
            payouts_enabled=bool(stripe_account.get("payouts_enabled")),
            details_submitted=bool(stripe_account.get("details_submitted")),
        )

        logger.info(
            "Connected account updated",
            extra={
                "event": "stripe_account_updated",
                "result": "success" if known else "ignored",
                "reason": f"account={stripe_account['id']}; charges_enabled={stripe_account.get('charges_enabled')}",
            },
        )

    @transactional
    def _revoke_account(self, *, account_id: str | None) -> None:
        """The tenant removed our access in their Stripe dashboard."""
        if not account_id:
            return

        known = self.stripe_account_repository.sync(stripe_account_id=account_id, revoked=True)

        logger.warning(
            "Connected account revoked our access",
            extra={
                "event": "stripe_account_revoked",
                "result": "success" if known else "ignored",
                "reason": f"account={account_id}",
            },
        )

    @staticmethod
    def _from_other_account(kind: str, expected: str | None, actual: str | None, reference) -> bool:
        """An event must come from the account the payment was made in."""
        if expected == actual:
            return False

        logger.warning(
            "Stripe event from the wrong account",
            extra={
                "event": "stripe_webhook_wrong_account",
                "result": "ignored",
                "reason": f"{kind}={reference}; expected={expected}; actual={actual}",
            },
        )

        return True

    @transactional
    def _settle(
        self,
        *,
        session,
        succeeded: bool,
        account_id: str | None,
    ) -> None:
        metadata = session.get("metadata") or {}

        if "payment_attempt_id" not in metadata:
            logger.warning(
                "Stripe checkout without our metadata",
                extra={
                    "event": "stripe_webhook_unmatched",
                    "result": "ignored",
                    "reason": session.get("id"),
                },
            )
            return

        # A webhook has no logged-in user, so act as the booking's user at
        # its location; RLS then applies as it would for them. The metadata
        # is trusted because the signature was verified. Stripe retries
        # deliveries, and the payment may have been settled without the
        # webhook: only a PENDING attempt moves.
        attempt = self.settlement.lock_pending(
            payment_attempt_id=UUID(metadata["payment_attempt_id"]),
            user_id=UUID(metadata["user_id"]),
            location_id=UUID(metadata["location_id"]),
        )

        if not attempt:
            return

        if self._from_other_account("payment_attempt", attempt.stripe_account_id, account_id, attempt.id):
            return

        self.settlement.settle(
            attempt=attempt,
            succeeded=succeeded,
            payment_intent_id=session.get("payment_intent"),
        )

    @transactional
    def _settle_refund(
        self,
        *,
        stripe_refund,
        account_id: str | None,
    ) -> None:
        """
        Finish one of our refunds. Succeeded: cancel the booking (releasing
        its place) and mark the refund processed. Failed or canceled: record
        it, so the family or staff can try again. Pending and
        requires_action wait for a later event.
        """
        metadata = stripe_refund.get("metadata") or {}

        # Refunds made by hand in the Stripe dashboard aren't ours to settle.
        if "refund_id" not in metadata:
            logger.warning(
                "Stripe refund without our metadata",
                extra={
                    "event": "stripe_refund_unmatched",
                    "result": "ignored",
                    "reason": stripe_refund.get("id"),
                },
            )
            return

        self.rls_context.set_user_id(user_id=UUID(metadata["user_id"]))
        self.rls_context.set_location_id(location_id=UUID(metadata["location_id"]))
        # Still reaches a family who has deactivated since asking.
        self.rls_context.set_payments_channel()

        refund = self.refund_repository.get_by_id(id=UUID(metadata["refund_id"]))

        # Stripe retries and sends several events per refund; only a
        # pending refund moves.
        if not refund or refund.status != RefundStatus.PENDING:
            return

        payment = self.refund_repository.get_payment(refund=refund)

        if self._from_other_account("refund", payment.stripe_account_id, account_id, refund.id):
            return

        # Saving Stripe's reply may have failed after the refund was made.
        if not refund.stripe_refund_id:
            self.refund_repository.mark_submitted(
                refund=refund,
                stripe_refund_id=stripe_refund["id"],
            )

        status = stripe_refund.get("status")

        if status == "succeeded":
            self.refund_repository.mark_succeeded(refund=refund)
            self.booking_repository.mark_refunded(booking_id=refund.booking_id)

            logger.info(
                "Refund completed",
                extra={
                    "event": "refund_completed",
                    "result": "success",
                    "reason": f"refund_id={refund.id}; booking_id={refund.booking_id}",
                },
            )

            # Once per refund: a repeated event finds it no longer pending.
            family = self.user_repository.get_by_id(id=refund.user_id)

            self.emails.queue(RefundConfirmationEmail(
                location_id=refund.location_id,
                user_id=family.id,
                to_email=family.email,
                first_name=family.first_name,
                reference=short_reference("RF", refund.id),
                amount_cents=refund.amount_cents,
                currency=refund.currency,
            ))

        elif status in ("failed", "canceled"):
            self.refund_repository.mark_failed(
                refund=refund,
                failure_reason=stripe_refund.get("failure_reason") or f"Stripe refund {status}",
            )

            logger.warning(
                "Refund failed",
                extra={
                    "event": "refund_failed",
                    "result": "failed",
                    "reason": f"refund_id={refund.id}; status={status}",
                },
            )
