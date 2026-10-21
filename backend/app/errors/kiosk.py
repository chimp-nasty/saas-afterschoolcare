from fastapi import status

from app.errors.base import ApplicationError


class KioskNotPairedError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "This kiosk isn't set up. Ask an admin for a setup code."
    result = "denied"


class KioskWrongKindError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "This can't be done from this kiosk."
    result = "denied"


class KioskSetupCodeInvalidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "That setup code isn't valid or has expired. Ask an admin for a new one."
    result = "failed"


class KioskSessionExpiredError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Your session has ended. Please start again."
    result = "denied"


class KioskPinChangeRequiredError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Choose your own PIN to continue."
    result = "denied"


class KioskLoginInvalidError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "That mobile number and PIN don't match."
    result = "failed"


class KioskLoginLockedError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Too many incorrect PINs. Choose Forgot PIN to get a new one."
    result = "denied"


class KioskPinExpiredError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Your PIN has expired. Choose Forgot PIN to get a new one."
    result = "denied"


class KioskDeviceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Kiosk not found"
    result = "failed"


class KioskKindTakenError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This centre already has a kiosk of that kind. Revoke it, or give it a new setup code."
    result = "denied"


class StaffKioskPinLockedError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Your staff PIN is locked after too many tries. Set a new one on the website."
    result = "denied"


class StaffKioskNoPinError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Set your staff PIN on the website first."
    result = "denied"


class StaffPinPasswordError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Your password isn't right."
    result = "failed"


class StaffKioskLoginInvalidError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "That PIN isn't right."
    result = "failed"


class StaffKioskPinRequiredError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Choose your name and enter your staff PIN."
    result = "denied"


class StaffKioskNotOnShiftError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Clock in on the Shifts tab first."
    result = "denied"


class StaffShiftEndTimeRequiredError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "You didn't clock out of your last shift. Enter the time you left first."
    result = "failed"


class StaffShiftEndTimeInvalidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The time you left must be after that shift started, and not in the future."
    result = "failed"
