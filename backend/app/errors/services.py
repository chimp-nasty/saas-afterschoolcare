from fastapi import status

from app.errors.base import ApplicationError


class LocationServiceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Location Service not found"
    result = "failed"


class LocationServiceNotPricedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Set a price above $0 before offering this service"
    result = "failed"


class LocationServiceTimesError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The session must finish after it starts"
    result = "failed"


class LocationServiceAgeRangeError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The youngest age can't be above the oldest"
    result = "failed"


class ServiceDayNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "That service day wasn't found"
    result = "failed"


class ServiceDayInPastError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Service days can't be added in the past"
    result = "failed"


class ServiceDayCapacityBelowBookedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Places can't go below the places already booked"
    result = "failed"


class ServiceDayCloseBookedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Children are booked on this day. Refund them before closing it"
    result = "failed"


class ServiceDayDeleteBookedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This day has had bookings, so it can't be deleted. Close it instead"
    result = "failed"
