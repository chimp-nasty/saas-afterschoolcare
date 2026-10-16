from datetime import date

from fastapi import status

from app.errors.base import ApplicationError


class BookingCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "One or more of these bookings already exist"
    result = "failed"


class BookingCapacityCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    result = "failed"

    def __init__(
        self,
        *,
        service_dates: list[date],
    ):
        super().__init__(
            message=(
                "No capacity available for: "
                + ", ".join(
                    service_date.strftime("%d/%m/%Y")
                    for service_date in service_dates
                )
            )
        )


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


class BookingGroupAlreadyPaidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Booking group is already marked as paid"
    result = "denied"


class BookingNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Booking not found"
    result = "failed"
