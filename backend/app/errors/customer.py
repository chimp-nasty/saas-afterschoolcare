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
        self.missing_fields = missing_fields
        super().__init__(
            message=self._build_message(missing_fields)
        )

    @staticmethod
    def _build_message(
        missing_fields: list[str],
    ) -> str:
        return (
            "Customer profile is incomplete. "
            f"Missing: {', '.join(missing_fields)}"
        )

class FamilyNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "That family isn't at this centre"
    result = "failed"


class EmergencyContactPhoneError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Your emergency contact needs a different phone number from yours"
    result = "denied"


class EmergencyContactRelationError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Say how your emergency contact is related to you"
    result = "denied"


class EmergencyContactFamilyOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only the family can change their emergency contact"
    result = "denied"


# Deactivated accounts (docs/account-deactivation.md).

class AccountDeactivatedError(ApplicationError):
    """Every request from a family deactivated at this centre (require_permission)."""

    status_code = status.HTTP_403_FORBIDDEN
    message = "This account is deactivated."
    result = "denied"


class DeactivationFamilyOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only family accounts can be deactivated."
    result = "denied"


class DeactivationUpcomingBookingsError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Cancel or refund your upcoming bookings before deactivating your account."
    result = "denied"


class AccountNotDeactivatedError(ApplicationError):
    """Asking to be reactivated, or reactivating, an account that's active."""

    status_code = status.HTTP_409_CONFLICT
    message = "This account isn't deactivated."
    result = "denied"


class EnquiryNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Enquiry not found"
    result = "failed"
