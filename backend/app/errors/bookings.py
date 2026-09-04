from datetime import date

from fastapi import status

from app.errors.base import ApplicationError
from app.public.schemas.booking import BookingConflictRow


class BookingCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    result = "failed"

    def __init__(
        self,
        *,
        conflicts: list[BookingConflictRow],
    ):
        self.message = self._build_message(conflicts)
        super().__init__()

    @staticmethod
    def _build_message(
        conflicts: list[BookingConflictRow],
    ) -> str:
        rows = [
            f"{conflict.child_name} - {conflict.service_date:%d/%m/%Y}"
            for conflict in conflicts
        ]

        return f"Bookings already exist: {', '.join(rows)}"


class BookingCapacityCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    result = "failed"

    def __init__(
        self,
        *,
        service_dates: list[date],
    ):
        self.message = (
            "No capacity available for: "
            + ", ".join(
                service_date.strftime("%d/%m/%Y")
                for service_date in service_dates
            )
        )

        super().__init__()


class MultipleBookingServicesError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Multiple Services selected"
    result = "failed"


class InvalidBookingServiceDaysError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid service day"
    result = "failed"


class BookingGroupAlreadyPaidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Booking group is already marked as paid"
    result = "denied"