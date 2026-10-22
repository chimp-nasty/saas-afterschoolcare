from fastapi import status

from app.errors.base import ApplicationError


class ActionNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Message not found"
    result = "failed"


class MessageAlreadyReadError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "The family has already read this message, so it can't be withdrawn"
    result = "denied"
