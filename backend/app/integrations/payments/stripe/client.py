from dataclasses import dataclass

import stripe

from app.core.config import settings


stripe.api_key = settings.STRIPE_SECRET_KEY


@dataclass
class StripePrice:
    amount_cents: int
    currency: str


@dataclass
class StripeCheckout:
    checkout_url: str
    checkout_session_id: str
    payment_intent_id: str | None


class StripeClient:
    def get_price(
        self,
        *,
        stripe_price_id: str,
    ) -> StripePrice:
        price = stripe.Price.retrieve(
            stripe_price_id,
        )

        if not price.active:
            raise ValueError(
                "Stripe price is inactive."
            )

        if price.unit_amount is None:
            raise ValueError(
                "Stripe price does not have a fixed unit amount."
            )

        return StripePrice(
            amount_cents=price.unit_amount,
            currency=price.currency.upper(),
        )