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
