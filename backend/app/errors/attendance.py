from fastapi import status

from app.errors.base import ApplicationError


class AttendanceKioskOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Children are signed in and out at the kiosk."
    result = "denied"


class AttendanceWrongKioskError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "This can't be done from this kiosk."
    result = "denied"


class StaffKioskAccessError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "This needs the centre's staff kiosk and a staff member of this centre."
    result = "denied"


class AttendanceBookingNotConfirmedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Only confirmed bookings can be signed in or out."
    result = "denied"


class AttendanceWrongDayError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Children can only be signed in or out on the day of their session."
    result = "denied"


class AttendanceNotOnPickupListError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "That person isn't on this family's pickup list."
    result = "denied"


class AttendanceCollectorNotApprovedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "A staff member needs to check your ID before you can collect children. Please find a staff member."
    result = "denied"


class AttendanceNotSignedInError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This child hasn't been signed in today. Please find a staff member."
    result = "denied"


class AttendanceCollectorRequiredError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Choose who collected the child, or name the person they were released to."
    result = "failed"


class KioskBookingNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "That session isn't one of today's for you."
    result = "failed"


class StaffPinStaffOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only staff have a staff PIN."
    result = "denied"


class AttendanceToSchoolServiceError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Only before school care children are sent to school."
    result = "failed"


class AttendanceOutsideServiceWindowError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Signing in and out opens 2 hours before the session and closes 2 hours after it."
    result = "denied"


class KioskSettingsAdminOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only this location's admins can change kiosk settings."
    result = "denied"
