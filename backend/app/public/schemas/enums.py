from enum import Enum, StrEnum


# API-facing enums. The database enum types live in migrations/schema and
# are mirrored as *Enum classes in the generated app/db/models.py; values
# compare equal across the two, so either can be passed to the other.


class AustralianState(str, Enum):
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    WA = "WA"
    SA = "SA"
    TAS = "TAS"
    ACT = "ACT"
    NT = "NT"


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


# The "My bookings" tabs. Lower case: the frontend uses these as tab ids.
class BookingGroupScope(StrEnum):
    UPCOMING = "upcoming"
    HISTORY = "history"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class PickupRelation(StrEnum):
    ACCOUNT_HOLDER = "account_holder"
    GRANDPARENT = "grandparent"
    AUNT_UNCLE = "aunt_uncle"
    FAMILY_FRIEND = "family_friend"
    NEIGHBOUR = "neighbour"
    NANNY_BABYSITTER = "nanny_babysitter"
    OTHER = "other"


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
