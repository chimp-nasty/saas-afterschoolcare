from fastapi import status

from app.errors.base import ApplicationError


class InvalidEmailWebhookError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid webhook"
    result = "denied"
