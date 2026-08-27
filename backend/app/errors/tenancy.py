from fastapi import status

from app.errors.base import ApplicationError


class LocationNotFoundError(ApplicationError):
    status = status.HTTP_404_NOT_FOUND
    message = "Invalid Location"
    result = "denied"