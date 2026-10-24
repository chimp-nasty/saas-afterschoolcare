from fastapi import status

from app.errors.base import ApplicationError


# The platform's site and registration (docs/tenant-administration.md,
# stage 4). Constraint names in migrations/schema/0002 and 0003, mapped in
# app/errors/database.py.
class InviteNotUsableError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This invite link can't be used any more. Ask for a new one"
    result = "denied"


class InviteNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Invite not found"
    result = "denied"


class TenantNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Business not found"
    result = "denied"


class TenantCodeTakenError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "That web address is taken. Choose another"
    result = "failed"


class TenantCodeReservedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "That web address belongs to the platform. Choose another"
    result = "failed"


class TenantActivePlatformOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only the platform can switch a business off or on"
    result = "denied"
