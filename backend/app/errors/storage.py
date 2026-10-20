from fastapi import status

from app.errors.base import ApplicationError


class StorageProviderError(ApplicationError):
    status_code = status.HTTP_502_BAD_GATEWAY
    message = "File storage error. Please try again."
    result = "failed"
