from fastapi import status

from app.errors.base import ApplicationError


class MedicalReviewDecisionNotAllowedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Staff can approve a child, request documentation, or reopen an approved child for review."
    result = "denied"


class DocumentationRequestMessageRequiredError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Say what documentation the family needs to provide."
    result = "failed"
