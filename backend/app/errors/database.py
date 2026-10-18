from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.errors.auth import UserCollisionError
from app.errors.base import ApplicationError
from app.errors.bookings import (
    BookingAttemptFinishedError,
    BookingCapacityCollisionError,
    BookingCollisionError,
    ChildNotMedicallyClearedError,
    InvalidBookingChildError,
    InvalidBookingServiceDaysError,
    ServiceDayClosedError,
    ServiceDayNotInFutureError,
)
from app.errors.children import ChildProfileCollisionError


class InvalidValueError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid value"
    result = "failed"


# Constraint names come from migrations/schema. Add an entry here when a
# constraint violation should reach the client as a specific error rather
# than a 500.
CONSTRAINT_ERRORS: dict[str, type[ApplicationError]] = {
    "uq_users_email": UserCollisionError,
    "uq_child_profile_active_identity": ChildProfileCollisionError,
    "uq_bookings_active_child_service_day": BookingCollisionError,
    # Reusing the idempotency key of a group that's already paid/expired.
    "uq_booking_groups_user_idempotency": BookingAttemptFinishedError,
    "fk_bookings_child": InvalidBookingChildError,
    "fk_bookings_location_service_day": InvalidBookingServiceDaysError,
    # Raised by the trg_bookings_enforce_rules trigger (schema/0008).
    "ck_bookings_service_day_in_future": ServiceDayNotInFutureError,
    "ck_bookings_service_day_open": ServiceDayClosedError,
    "ck_bookings_service_day_full": BookingCapacityCollisionError,
    "ck_bookings_child_medically_cleared": ChildNotMedicallyClearedError,
}


def map_integrity_error(exc: IntegrityError) -> Exception:
    """
    Translate a constraint violation into its ApplicationError, by the
    violated constraint's name. Unmapped violations are returned unchanged
    (and surface as a 500).
    """
    diag = getattr(exc.orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)

    if constraint in CONSTRAINT_ERRORS:
        return CONSTRAINT_ERRORS[constraint](log_reason=constraint)

    # Every CHECK constraint is named ck_<table>_<rule>.
    if constraint and constraint.startswith("ck_"):
        return InvalidValueError(log_reason=constraint)

    return exc
