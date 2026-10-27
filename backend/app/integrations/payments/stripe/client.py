import time
from dataclasses import dataclass

import requests
import stripe

from app.core.config import settings
from app.errors.payments import PaymentProviderError


stripe.api_key = settings.STRIPE_SECRET_KEY

# Stripe's minimum. Pending bookings hold capacity until the session
# completes or expires, so keep this short.
CHECKOUT_EXPIRY_SECONDS = 30 * 60

# Connected accounts and their onboarding links are made with Stripe's
# Accounts v2 API, which Stripe requires for new Connect integrations. The
# installed SDK (stripe 9.x) predates v2, so these two calls are plain HTTP
# with a v2 API version. Everything else (checkouts, refunds, reading an
# account's flags) stays on v1, which works with v2 accounts.
_STRIPE_V2_URL = "https://api.stripe.com/v2"
_STRIPE_V2_VERSION = "2026-09-30.endive"
_STRIPE_V2_TIMEOUT_SECONDS = 30


def webhooks_configured(*, connect: bool) -> bool:
    """
    Whether the webhook endpoint a payment's events arrive on has a real
    signing secret (not empty, nor the deploy runbook's "unset"
    placeholder). Without one, a family could pay and nothing would ever
    hear of it, so checkout is refused (docs/payment-confirmation.md).
    `connect`: the Connect endpoint, for tenants' connected accounts.
    """
    secret = settings.STRIPE_CONNECT_WEBHOOK_SECRET if connect else settings.STRIPE_WEBHOOK_SECRET

    return bool(secret) and secret.startswith("whsec_")


@dataclass
class StripeCheckout:
    checkout_url: str | None
    checkout_session_id: str
    payment_intent_id: str | None
    status: str  # "open", "complete" or "expired"
    # "paid", "unpaid" (a delayed method still settling, or not paid yet)
    # or "no_payment_required".
    payment_status: str


@dataclass
class StripeRefund:
    refund_id: str
    status: str  # "pending", "requires_action", "succeeded", "failed" or "canceled"


@dataclass
class StripeAccount:
    """A tenant's connected account, as Stripe reports it."""

    account_id: str
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool


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
        payment_status=session.payment_status,
    )


def _to_account(account) -> StripeAccount:
    return StripeAccount(
        account_id=account.id,
        charges_enabled=bool(account.charges_enabled),
        payouts_enabled=bool(account.payouts_enabled),
        details_submitted=bool(account.details_submitted),
    )


class StripeClient:
    """
    Every Stripe call. With `account_id`, payments and refunds are made in
    that tenant's connected account (Stripe Connect, direct charges): the
    platform's key, acting for the account. Without one, the platform's
    own account (connected-account management, and seeded payments).
    """

    def __init__(self, *, account_id: str | None = None):
        self.account_id = account_id

    def _as_account(self) -> dict:
        return {"stripe_account": self.account_id} if self.account_id else {}

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
                **self._as_account(),
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
            session = stripe.checkout.Session.retrieve(checkout_session_id, **self._as_account())
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
            session = stripe.checkout.Session.expire(checkout_session_id, **self._as_account())
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
                **self._as_account(),
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
                **self._as_account(),
            )
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return StripeRefund(
            refund_id=refund.id,
            status=refund.status,
        )

    # --- Connected accounts (the platform's own calls) ----------------------

    def _v2_post(self, path: str, body: dict) -> dict:
        """POST to Stripe's v2 API with the platform's key."""
        try:
            response = requests.post(
                f"{_STRIPE_V2_URL}{path}",
                json=body,
                headers={
                    "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                    "Stripe-Version": _STRIPE_V2_VERSION,
                },
                timeout=_STRIPE_V2_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        if not response.ok:
            raise PaymentProviderError(log_reason=f"Stripe {path} {response.status_code}: {response.text[:500]}")

        return response.json()

    def create_account(
        self,
        *,
        email: str | None,
        business_name: str,
    ) -> StripeAccount:
        """
        A connected account in Australia for a tenant, as a merchant taking
        card payments. Standard-style: the centre signs in to the full Stripe
        dashboard, and Stripe collects its fees and carries its losses
        (direct charges). New, so nothing is enabled until onboarding.
        """
        body = {
            "display_name": business_name,
            "identity": {"country": "au"},
            "dashboard": "full",
            "defaults": {
                "currency": "aud",
                "responsibilities": {"fees_collector": "stripe", "losses_collector": "stripe"},
            },
            "configuration": {"merchant": {"capabilities": {"card_payments": {"requested": True}}}},
        }

        if email:
            body["contact_email"] = email

        account = self._v2_post("/core/accounts", body)

        return StripeAccount(
            account_id=account["id"],
            charges_enabled=False,
            payouts_enabled=False,
            details_submitted=False,
        )

    def get_account(
        self,
        *,
        account_id: str,
    ) -> StripeAccount:
        """The account's flags, read through v1 (which reads v2 accounts too)."""
        try:
            account = stripe.Account.retrieve(account_id)
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return _to_account(account)

    def create_onboarding_link(
        self,
        *,
        account_id: str,
        refresh_url: str,
        return_url: str,
    ) -> str:
        """Stripe's hosted onboarding for the account (a one-time link)."""
        link = self._v2_post(
            "/core/account_links",
            {
                "account": account_id,
                "use_case": {
                    "type": "account_onboarding",
                    "account_onboarding": {
                        "refresh_url": refresh_url,
                        "return_url": return_url,
                    },
                },
            },
        )

        return link["url"]

    def oauth_authorize_url(
        self,
        *,
        state: str,
        redirect_uri: str,
    ) -> str:
        """
        "Connect with Stripe": Stripe's page where a business logs in and
        picks its existing account (or makes one) to link to the platform.
        """
        return stripe.OAuth.authorize_url(
            client_id=settings.STRIPE_CONNECT_CLIENT_ID,
            response_type="code",
            scope="read_write",
            state=state,
            redirect_uri=redirect_uri,
        )

    def complete_oauth(
        self,
        *,
        code: str,
    ) -> str:
        """Finish linking: Stripe's one-time code for the linked account's id."""
        try:
            token = stripe.OAuth.token(grant_type="authorization_code", code=code)
        except stripe.StripeError as exc:
            raise PaymentProviderError(log_reason=str(exc)) from exc

        return token["stripe_user_id"]

    def construct_webhook_event(
        self,
        *,
        payload: bytes,
        signature: str,
        connect: bool = False,
    ):
        """
        Verify a webhook's signature; raises on a forged or stale event.
        `connect`: the Connect endpoint (events on connected accounts), with
        its own signing secret.
        """
        secret = settings.STRIPE_CONNECT_WEBHOOK_SECRET if connect else settings.STRIPE_WEBHOOK_SECRET

        if not secret:
            raise ValueError("No signing secret for this webhook endpoint")

        return stripe.Webhook.construct_event(
            payload,
            signature,
            secret,
        )
