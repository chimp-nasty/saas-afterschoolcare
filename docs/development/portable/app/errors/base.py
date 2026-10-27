import re
from fastapi import status


class ApplicationError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    message: str = "Something went wrong"
    result: str = "failed"

    def __init__(
        self,
        *,
        message: str | None = None,
        log_reason: str | None = None,
    ):
        self.message = message or type(self).message
        self.log_reason = log_reason

        super().__init__(self.message)

    @property
    def event(self) -> str:
        name = type(self).__name__.removesuffix("Error")

        value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)

        return value.lower()