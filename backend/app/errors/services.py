from fastapi import status

from app.errors.base import ApplicationError


class LocationServiceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Location Service not found"
    result = "failed"


class LocationServiceNotPricedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Set a price above $0 before offering this service"
    result = "failed"
