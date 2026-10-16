from datetime import date

from fastapi import status

from app.errors.base import ApplicationError


class LocationServiceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Location Service not found"
    result = "failed"


class LocationServiceNotLinkedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This service is not linked to a Stripe product"
    result = "failed"
