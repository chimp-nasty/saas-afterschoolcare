from fastapi import status

from app.errors.base import ApplicationError


class ChildProfileCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Child Profile already exists"
    result = "failed"