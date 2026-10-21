from fastapi import status

from app.errors.base import ApplicationError


class ChildDocumentNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Document not found"
    result = "failed"


class ChildDocumentFamilyOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only the child's family can add or remove their documents."
    result = "denied"


class ChildDocumentChangeNotAllowedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This document can't be changed. Upload a new one instead."
    result = "denied"


class ChildDocumentTypeNotAllowedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Upload a PDF, JPEG, PNG or HEIC file."
    result = "failed"


class ChildDocumentTooLargeError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Files must be 10 MB or smaller."
    result = "failed"


class ChildDocumentNotReceivedError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "We didn't receive the file. Try uploading it again."
    result = "failed"


class ChildDocumentInvalidFileError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This file isn't a readable PDF, JPEG, PNG or HEIC. Check the file and upload it again."
    result = "failed"


class ChildDocumentUploadFailedError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    message = "This upload didn't go through. Upload the file again."
    result = "failed"


class ChildDocumentPrintStaffOnlyError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Only staff on shift at the staff kiosk can mark a plan printed."
    result = "denied"
