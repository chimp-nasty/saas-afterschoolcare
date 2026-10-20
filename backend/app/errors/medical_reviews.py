from fastapi import status

from app.errors.base import ApplicationError


class MedicalReviewDecisionNotAllowedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Staff can approve a child or request documentation. Reviews are reopened when the family updates the child's details."
    result = "denied"


class DocumentationRequestMessageRequiredError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Say what documentation the family needs to provide."
    result = "failed"
