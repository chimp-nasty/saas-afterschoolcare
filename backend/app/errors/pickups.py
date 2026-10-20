from fastapi import status

from app.errors.base import ApplicationError


class PickupNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Pickup person not found"
    result = "failed"


class AccountHolderPickupError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Your own pickup details come from your profile. Update them in Account → Profile."
    result = "denied"


class PickupLimitReachedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "You can have up to 3 pickup people. Remove one to add another."
    result = "denied"


class PickupPhoneOnListError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This phone number is already on your pickup list."
    result = "failed"


class PickupPhoneTakenError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This phone number is already registered at this centre. Use a different number, or contact the centre."
    result = "denied"


class PickupEmailOnListError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This email is already on your pickup list."
    result = "failed"


class PickupEmailTakenError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This email is already registered at this centre. Use a different email, or contact the centre."
    result = "denied"


class PickupPhoneInvalidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Enter a valid Australian phone number"
    result = "failed"


class PickupConsentRequiredError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Confirm that the people on your pickup list may collect this child."
    result = "denied"
