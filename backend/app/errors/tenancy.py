from fastapi import status

from app.errors.base import ApplicationError


class LocationNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Invalid Location"
    result = "denied"


# Business settings (docs/tenant-administration.md): constraint names in
# migrations/schema/0002_tenancy.sql, mapped in app/errors/database.py.
class AbnInvalidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "That ABN isn't valid. Check the 11 digits"
    result = "failed"


class LocationCodeTakenError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "Another of your centres already uses that web address"
    result = "failed"


class LocationCodeReservedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "That web address is used by the site itself. Choose another"
    result = "failed"


class LocationTimezoneError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Choose an Australian time zone"
    result = "failed"


# The business's site (stage 5): its logo, icon and policy documents.
class SiteFileInvalidError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "That file can't be used. Logos are PNG, JPEG or WebP up to 1 MB; policies are PDFs up to 5 MB"
    result = "failed"


class SiteIconShapeError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The site icon must be square and at least 192 by 192 pixels"
    result = "failed"


class SiteFileNotReceivedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "The file hasn't arrived yet. Please try uploading it again"
    result = "failed"


class SiteFileNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found"
    result = "denied"


class SiteColourError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Colours are written like #5E2BFF"
    result = "failed"


class FaqLimitError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "You can have at most 20 questions"
    result = "failed"
