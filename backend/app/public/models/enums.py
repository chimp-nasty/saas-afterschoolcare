from enum import StrEnum


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


class StripeStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class CurrencyCode(StrEnum):
    AUD = "AUD"
    NZD = "NZD"
    USD = "USD"


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class ChildDocumentType(StrEnum):
    MEDICAL_ACTION_PLAN = "medical_action_plan"
    ASTHMA_ACTION_PLAN = "asthma_action_plan"
    ALLERGY_ANAPHYLAXIS_PLAN = "allergy_anaphylaxis_plan"
    OTHER = "other"


class ChildDocumentUploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"


class MedicalReviewStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    DOCUMENTATION_REQUESTED = "documentation_requested"
    APPROVED = "approved"