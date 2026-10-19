from fastapi import status

from app.errors.base import ApplicationError


class ChildProfileCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Child Profile already exists"
    result = "failed"


class ChildProfileNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Child Profile not found"
    result = "failed"


class ChildProfileInactiveError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This child has been removed"
    result = "failed"


class ChildHasUpcomingBookingsError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This child has upcoming bookings. Cancel or refund them before removing the child."
    result = "denied"


class ChildAgeOutOfRangeError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    result = "denied"

    def __init__(
        self,
        *,
        min_age: int,
        max_age: int,
    ):
        super().__init__(
            message=f"Children must be aged {min_age} to {max_age}"
        )
