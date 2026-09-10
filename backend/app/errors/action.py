from fastapi import status

from app.errors.base import ApplicationError


class ActionNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Action not found"
    result = "failed"