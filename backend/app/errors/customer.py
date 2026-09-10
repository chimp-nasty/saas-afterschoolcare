from fastapi import status

from app.errors.base import ApplicationError


class CustomerProfileNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Customer profile not found"
    result = "failed"
    

class CustomerProfileIncompleteError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    result = "denied"

    def __init__(
        self,
        *,
        missing_fields: list[str],
    ):
        self.message = self._build_message(missing_fields)
        self.missing_fields = missing_fields
        super().__init__()

    @staticmethod
    def _build_message(
        missing_fields: list[str],
    ) -> str:
        return (
            "Customer profile is incomplete. "
            f"Missing: {', '.join(missing_fields)}"
        )