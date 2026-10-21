from fastapi import status

from app.errors.base import ApplicationError


class RefundNotAllowedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This session can't be refunded. It may be past the refund window or not paid."
    result = "denied"


class RefundAlreadyRequestedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "A refund has already been requested for this session."
    result = "failed"


class RefundNoCardPaymentError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This booking has no card payment to refund (it was marked paid another way)."
    result = "denied"
