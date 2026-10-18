from fastapi import status

from app.errors.base import ApplicationError


class BookingCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "One or more of these bookings already exist"
    result = "failed"


class BookingCapacityCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "No capacity available for one or more of the selected days"
    result = "failed"


class MultipleBookingServicesError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Multiple Services selected"
    result = "failed"


class InvalidBookingServiceDaysError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid service day"
    result = "failed"


class InvalidBookingChildError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid child for this booking"
    result = "denied"


class ServiceDayNotInFutureError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Bookings must be for a future date"
    result = "denied"


class ServiceDayClosedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This service day is closed"
    result = "denied"


class ChildNotMedicallyClearedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This child is awaiting medical review and can't be booked yet"
    result = "denied"


class CheckoutOriginError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Bookings must be made from this location's site"
    result = "denied"


class BookingAttemptFinishedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This booking has already been completed or has expired. Please start a new booking."
    result = "denied"


class CheckoutNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Checkout not found"
    result = "failed"


class BookingGroupAlreadyPaidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Booking group is already marked as paid"
    result = "denied"


class BookingGroupNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Booking not found"
    result = "failed"


class BookingNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Booking not found"
    result = "failed"
