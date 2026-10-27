from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.errors.base import ApplicationError


class InvalidValueError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid value"
    result = "failed"


# Populate with this project's named constraints and trigger-raised rules.
CONSTRAINT_ERRORS: dict[str, type[ApplicationError]] = {}


def map_integrity_error(exc: IntegrityError) -> Exception:
    diag = getattr(exc.orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)

    if constraint in CONSTRAINT_ERRORS:
        return CONSTRAINT_ERRORS[constraint](log_reason=constraint)

    if constraint and constraint.startswith("ck_"):
        return InvalidValueError(log_reason=constraint)

    return exc
