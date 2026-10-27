from fastapi import status

from app.errors.base import ApplicationError


class LimitExceeded(ApplicationError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Rate limit exceeded"
    result = "denied"
