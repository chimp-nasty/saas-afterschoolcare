from datetime import date

from fastapi import status

from app.errors.base import ApplicationError


class LocationServiceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    msg = "Location Service not found"
    result = "failed"