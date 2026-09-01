from fastapi import status

from app.errors.base import ApplicationError


class JwtMissingError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication token is required"
    result = "denied"


class JwtInvalidError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication token is invalid"
    result = "denied"


class JwtExpiredError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication token has expired"
    result = "denied"


class JwtForbiddenError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Authentication token is not permitted"
    result = "denied"
    

class LimitExceeded(ApplicationError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Rate limit exceeded"
    result = "denied"


class AuthenticationFailedError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication failed"
    result = "denied"


class PermissionNotFoundError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Required permission not found"
    result = "denied"


class ForbiddenError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "You are not permitted to perform this action"
    result = "denied"
    
    
class UserCollisionError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "User already exists"
    result = "denied"


class UserNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "User not found"
    result = "failed"
    

class InvalidPasswordResetError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid or expired password reset token"
    result = "failed"


class RoleNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Role not found"
    result = "failed"