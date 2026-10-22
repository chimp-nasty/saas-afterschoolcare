from fastapi import status

from app.errors.base import ApplicationError


class PaymentProviderError(ApplicationError):
    status_code = status.HTTP_502_BAD_GATEWAY
    message = "Payment provider error. Please try again."
    result = "failed"


class InvalidWebhookError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid webhook"
    result = "denied"


class PaymentsNotEnabledError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This centre isn't taking bookings online yet"
    result = "denied"


class StripeAccountNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "No Stripe account is connected"
    result = "failed"


class StripeAccountRevokedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This payment's Stripe account no longer allows us access. Refund it in your Stripe dashboard."
    result = "denied"


class StripeAccountTakenError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "That Stripe account is already connected to another business"
    result = "denied"


class StripeOAuthUnavailableError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Connecting an existing Stripe account isn't set up yet"
    result = "denied"


class StripeOAuthStateError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This Stripe link has expired. Start again from Admin › Payments."
    result = "denied"


class StripeAccountLinkedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This is your own Stripe account. Finish setting it up in your Stripe dashboard, then refresh the status here."
    result = "denied"
