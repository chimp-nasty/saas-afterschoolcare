from datetime import datetime

from pydantic import BaseModel


class StripeAccountStatusResponse(BaseModel):
    """The business's Stripe account, as Admin › Payments shows it."""

    # A Stripe account has been created for the business.
    connected: bool
    # Its id (acct_...), to find it in Stripe's dashboard.
    stripe_account_id: str | None
    # Stripe's own flags: onboarding finished, card payments on, payouts on.
    details_submitted: bool
    charges_enabled: bool
    payouts_enabled: bool
    # Payments turned off in our app (refunds of past payments still work).
    disconnected: bool
    # The business removed our access in their Stripe dashboard.
    revoked: bool
    # Everything above lines up: families can book and pay.
    takes_payments: bool
    connected_at: datetime | None
    # "Connect with Stripe" (linking an existing account) is set up.
    can_link_existing: bool


class StripeOnboardingResponse(BaseModel):
    """Stripe's hosted onboarding page, to send the superadmin to (one use)."""

    url: str
