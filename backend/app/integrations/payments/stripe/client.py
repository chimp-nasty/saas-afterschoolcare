import time
from dataclasses import dataclass

import stripe

from app.core.config import settings
from app.errors.payments import PaymentProviderError


stripe.api_key = settings.STRIPE_SECRET_KEY

# Stripe's minimum. Pending bookings hold capacity until the session
# completes or expires, so keep this short.
CHECKOUT_EXPIRY_SECONDS = 30 * 60


@dataclass
class StripeCheckout:
    checkout_url: str | None
    checkout_session_id: str
    payment_intent_id: str | None
    status: str  # "open", "complete" or "expired"


@dataclass
class StripeRefund:
    refund_id: str
    status: str  # "pending", "requires_action", "succeeded", "failed" or "canceled"


@dataclass
class CheckoutLineItem:
    description: str
    amount_cents: int


def _currency_code(currency) -> str:
    """
    Stripe's lowercase code. Accepts a plain string or an enum member:
    str() of the generated (str, Enum) classes gives "CurrencyCodeEnum.AUD",
    not "AUD", so read the value instead.
    """
    return getattr(currency, "value", currency).lower()


def _to_checkout(session) -> StripeCheckout:
    return StripeCheckout(
        checkout_url=session.url,
        checkout_session_id=session.id,
        payment_intent_id=session.payment_intent,
        status=session.status,
    )


class StripeClient:
    def create_checkout_session(
        self,
        *,
        line_items: list[CheckoutLineItem],
        currency: str,
        metadata: dict[str, str],
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
    ) -> StripeCheckout:
        """
        A hosted Checkout page for a one-off payment. Prices come from our
        booking snapshots (price_data): our database is the only source of
        prices, so there's no Stripe catalogue to keep in step.
        """
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": _currency_code(currency),
                            "unit_amount": item.amount_cents,
                            "product_data": {"name": item.description},
                        },
                    }
                    for item in line_items
                ],
                metadata=metadata,
                payment_intent_data={"metadata": metadata},
                client_reference_id=metadata.get("booking_group_id"),
                success_url=success_url,
                cancel_url=cancel_url,
                expires_at=int(time.time()) + CHECKOUT_EXPIRY_SECONDS,
                idempotency_key=idempotency_key,
            )
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return _to_checkout(session)

    def get_checkout_session(
        self,
        *,
        checkout_session_id: str,
    ) -> StripeCheckout:
        try:
            session = stripe.checkout.Session.retrieve(checkout_session_id)
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return _to_checkout(session)

    def expire_checkout_session(
        self,
        *,
        checkout_session_id: str,
    ) -> StripeCheckout:
        """Close an open session so it can no longer be paid."""
        try:
            session = stripe.checkout.Session.expire(checkout_session_id)
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return _to_checkout(session)

    def get_receipt_url(
        self,
        *,
        payment_intent_id: str,
    ) -> str | None:
        """
        The Stripe-hosted receipt for a payment (it also shows any refunds).
        It's on the payment's charge, not the checkout session.
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(
                payment_intent_id,
                expand=["latest_charge"],
            )
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        charge = payment_intent.latest_charge

        return charge.receipt_url if charge else None

    def create_refund(
        self,
        *,
        payment_intent_id: str,
        amount_cents: int,
        metadata: dict[str, str],
        idempotency_key: str,
    ) -> StripeRefund:
        """
        Refund part of a payment (one booking) to the card it came from.
        The full amount goes back; the centre absorbs Stripe's fee.
        """
        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount_cents,
                reason="requested_by_customer",
                metadata=metadata,
                idempotency_key=idempotency_key,
            )
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return StripeRefund(
            refund_id=refund.id,
            status=refund.status,
        )

    def construct_webhook_event(
        self,
        *,
        payload: bytes,
        signature: str,
    ):
        """Verify a webhook's signature; raises on a forged or stale event."""
        return stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
