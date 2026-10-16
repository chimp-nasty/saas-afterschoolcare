from fastapi import status

from app.errors.base import ApplicationError


class ChildProfileCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Child Profile already exists"
    result = "failed"


class ChildProfileNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Child Profile not found"
    result = "failed"