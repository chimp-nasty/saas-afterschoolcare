from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.errors.attendance import (
    AttendanceOutsideServiceWindowError,
    KioskSettingsAdminOnlyError,
    AttendanceToSchoolServiceError,
    AttendanceBookingNotConfirmedError,
    AttendanceCollectorNotApprovedError,
    AttendanceCollectorRequiredError,
    AttendanceNotOnPickupListError,
    AttendanceNotSignedInError,
    AttendanceKioskOnlyError,
    AttendanceWrongDayError,
    AttendanceWrongKioskError,
    KioskBookingNotFoundError,
    StaffKioskAccessError,
    StaffPinStaffOnlyError,
)
from app.errors.auth import UserCollisionError
from app.errors.kiosk import KioskKindTakenError, StaffKioskNotOnShiftError
from app.errors.base import ApplicationError
from app.errors.bookings import (
    BookingAttemptFinishedError,
    BookingCapacityCollisionError,
    BookingCollisionError,
    ChildAgeNotEligibleError,
    ChildInactiveError,
    ChildNotMedicallyClearedError,
    InvalidBookingChildError,
    InvalidBookingServiceDaysError,
    ServiceDayClosedError,
    ServiceNotOfferedError,
    ServiceDayNotInFutureError,
)
from app.errors.child_documents import (
    ChildDocumentChangeNotAllowedError,
    ChildDocumentFamilyOnlyError,
    ChildDocumentNotFoundError,
    ChildDocumentPrintStaffOnlyError,
    ChildDocumentTooLargeError,
    ChildDocumentTypeNotAllowedError,
)
from app.errors.children import (
    ChildProfileCollisionError,
    ChildProfileInactiveError,
)
from app.errors.medical_reviews import (
    DocumentationRequestMessageRequiredError,
    MedicalReviewDecisionNotAllowedError,
)
from app.errors.services import LocationServiceNotPricedError
from app.errors.refunds import (
    RefundAlreadyRequestedError,
    RefundNoCardPaymentError,
    RefundNotAllowedError,
)
from app.errors.pickups import (
    PickupConsentRequiredError,
    PickupEmailOnListError,
    PickupEmailTakenError,
    PickupLimitReachedError,
    PickupPhoneInvalidError,
    PickupPhoneOnListError,
    PickupPhoneTakenError,
    PinFormatError,
    PinReusedError,
)


class InvalidValueError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid value"
    result = "failed"


# Constraint names come from migrations/schema. Add an entry here when a
# constraint violation should reach the client as a specific error rather
# than a 500.
CONSTRAINT_ERRORS: dict[str, type[ApplicationError]] = {
    "uq_users_email": UserCollisionError,
    "uq_child_profile_active_identity": ChildProfileCollisionError,
    "uq_bookings_active_child_service_day": BookingCollisionError,
    # Reusing the idempotency key of a group that's already paid/expired.
    "uq_booking_groups_user_idempotency": BookingAttemptFinishedError,
    "fk_bookings_child": InvalidBookingChildError,
    "fk_bookings_location_service_day": InvalidBookingServiceDaysError,
    # Raised by the trg_bookings_enforce_rules trigger (schema/0008).
    "ck_bookings_service_day_in_future": ServiceDayNotInFutureError,
    "ck_bookings_service_day_open": ServiceDayClosedError,
    "ck_bookings_service_offered": ServiceNotOfferedError,
    "ck_bookings_service_day_full": BookingCapacityCollisionError,
    "ck_bookings_child_medically_cleared": ChildNotMedicallyClearedError,
    "ck_bookings_child_active": ChildInactiveError,
    "ck_bookings_child_age": ChildAgeNotEligibleError,
    # Pickup people (schema/0004). The phone rules also apply when an
    # account holder's profile phone changes (their row follows it).
    "uq_authorized_pickup_persons_family_phone": PickupPhoneOnListError,
    "ex_authorized_pickup_persons_tenant_phone": PickupPhoneTakenError,
    "ck_authorized_pickup_persons_phone_format": PickupPhoneInvalidError,
    "uq_authorized_pickup_persons_family_email": PickupEmailOnListError,
    "ex_authorized_pickup_persons_tenant_email": PickupEmailTakenError,
    "ck_authorized_pickup_persons_limit": PickupLimitReachedError,
    "ck_child_profile_pickup_consent": PickupConsentRequiredError,
    # Refunds (schema/0004): the window and one active refund per booking.
    "ck_refunds_booking_refundable": RefundNotAllowedError,
    "ck_refunds_card_payment": RefundNoCardPaymentError,
    "uq_refunds_active_booking": RefundAlreadyRequestedError,
    "ck_location_service_config_active_priced": LocationServiceNotPricedError,
    # Child documents (schema/0004): the table's checks and
    # trg_child_documents_rules.
    "ck_child_documents_family_only": ChildDocumentFamilyOnlyError,
    "ck_child_documents_child_active": ChildProfileInactiveError,
    "ck_child_documents_change": ChildDocumentChangeNotAllowedError,
    "ck_child_documents_content_type": ChildDocumentTypeNotAllowedError,
    "ck_child_documents_size": ChildDocumentTooLargeError,
    # Medical review (schema/0004): trg_child_medical_state_rules.
    "ck_child_medical_state_staff_decision": MedicalReviewDecisionNotAllowedError,
    "ck_child_medical_state_documentation_request": DocumentationRequestMessageRequiredError,
    # Attendance (schema/0004): trg_attendance_records_rules, the table's
    # checks and the kiosk functions.
    "ck_attendance_records_kiosk_only": AttendanceKioskOnlyError,
    "ck_attendance_records_kiosk_kind": AttendanceWrongKioskError,
    "ck_staff_kiosk_access": StaffKioskAccessError,
    "ck_staff_kiosk_on_shift": StaffKioskNotOnShiftError,
    "ck_attendance_records_booking_confirmed": AttendanceBookingNotConfirmedError,
    "ck_attendance_records_service_day": AttendanceWrongDayError,
    "ck_attendance_records_family_person": AttendanceNotOnPickupListError,
    "ck_attendance_records_collector_approved": AttendanceCollectorNotApprovedError,
    "ck_attendance_records_collected_by": AttendanceCollectorRequiredError,
    "ck_attendance_records_not_signed_in": AttendanceNotSignedInError,
    "ck_attendance_records_to_school_service": AttendanceToSchoolServiceError,
    "ck_child_documents_printed_document": ChildDocumentNotFoundError,
    "ck_child_documents_printed_by_staff": ChildDocumentPrintStaffOnlyError,
    "ck_attendance_records_service_window": AttendanceOutsideServiceWindowError,
    "ck_locations_kiosk_settings_admin": KioskSettingsAdminOnlyError,
    "ck_attendance_records_kiosk_booking": KioskBookingNotFoundError,
    # Kiosk PINs (schema/0004): kiosk_change_pin.
    "ck_authorized_pickup_persons_pin_format": PinFormatError,
    "ck_authorized_pickup_persons_pin_reused": PinReusedError,
    # One active kiosk of each kind per location (schema/0004).
    "uq_location_kiosk_devices_active_kind": KioskKindTakenError,
    # Staff PINs (schema/0004): set_staff_pin.
    "ck_staff_pins_staff_only": StaffPinStaffOnlyError,
    "ck_staff_pins_pin_format": PinFormatError,
}


def map_integrity_error(exc: IntegrityError) -> Exception:
    """
    Translate a constraint violation into its ApplicationError, by the
    violated constraint's name. Unmapped violations are returned unchanged
    (and surface as a 500).
    """
    diag = getattr(exc.orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)

    if constraint in CONSTRAINT_ERRORS:
        return CONSTRAINT_ERRORS[constraint](log_reason=constraint)

    # Every CHECK constraint is named ck_<table>_<rule>.
    if constraint and constraint.startswith("ck_"):
        return InvalidValueError(log_reason=constraint)

    return exc
