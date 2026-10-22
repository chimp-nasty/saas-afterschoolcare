from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel


class RollEntryResponse(BaseModel):
    """One child's session on the roll, and where it's up to."""

    booking_id: UUID
    child_id: UUID
    child_first_name: str
    child_last_name: str

    family_user_id: UUID
    family_first_name: str
    family_last_name: str
    family_phone: str | None
    # The family's emergency contact, for when the parent can't be reached.
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None
    emergency_contact_relation_other: str | None

    service_name: str
    start_time: time
    end_time: time

    signed_in_at: datetime | None
    signed_in_by: str | None
    signed_out_at: datetime | None
    # The staff member who recorded it (None when signed out at the family kiosk).
    signed_out_by: str | None
    # Who took the child: an approved pickup person, or a one-off release.
    collected_by: str | None
    # Whether the collector's photo ID had been sighted by the sign-out
    # (None for a one-off release or no sign-out).
    collector_id_sighted: bool | None
    released_to_name: str | None
    release_note: str | None
    # Before school care: staff sent them to school.
    sent_to_school: bool

    # Still signed in after the session ended.
    is_late: bool


class RollPickupPersonResponse(BaseModel):
    """Someone on a family's pickup list, as staff see it."""

    pickup_person_id: UUID
    first_name: str
    last_name: str
    relation: str
    phone: str
    identity_verified_at: datetime | None
    staff_approved_at: datetime | None


class RollFamilyResponse(BaseModel):
    family_user_id: UUID
    pickups: list[RollPickupPersonResponse]


class RollResponse(BaseModel):
    """
    A day's roll at the location: every confirmed booking, and each booked
    family's pickup list (who may collect, and who's approved), so staff
    have what they need if the kiosks are down.
    """

    date: date
    entries: list[RollEntryResponse]
    families: list[RollFamilyResponse]


class AttendanceTimesResponse(BaseModel):
    """A session's attendance after a change."""

    booking_id: UUID
    signed_in_at: datetime | None
    signed_out_at: datetime | None


class StaffShiftResponse(BaseModel):
    """The shift that was started or ended (both empty: there wasn't one to end)."""

    started_at: datetime | None
    ended_at: datetime | None


class RunSheetEntryResponse(BaseModel):
    """
    A child on the run sheet (the staff kiosk before anyone enters a PIN,
    and the admin run sheet): name, session and where they're up to, who
    signed them in and out (short names), and whether they have medical
    details or documents (no details).
    """

    booking_id: UUID
    child_id: UUID
    child_first_name: str
    child_last_name: str
    family_user_id: UUID
    service_name: str
    start_time: time
    end_time: time
    signed_in_at: datetime | None
    # Names as "Sam L." before anyone enters a PIN.
    signed_in_by: str | None
    signed_out_at: datetime | None
    collected_by: str | None
    collector_id_sighted: bool | None
    released_to: str | None
    sent_to_school: bool
    is_late: bool
    has_medical: bool
    medical_review_status: str | None
    # Staff have written notes about the child (read at the kiosk).
    has_notes: bool


class RunSheetSessionResponse(BaseModel):
    """
    One service running that day (a tab on the run sheet) and its places.
    Children on the run sheet are matched to it by service and times.
    """

    location_service_day_id: UUID
    # e.g. before_school_care: decides the tab's bulk action.
    service_code: str
    service_name: str
    start_time: time
    end_time: time
    is_open: bool
    capacity: int
    # Confirmed bookings: the children on the run sheet.
    booked: int
    # What families can still book (the booking rules' count).
    places_left: int
    # Places held by bookings still awaiting payment (not on the run sheet).
    awaiting_payment: int
    # When signing in and out opens and closes (None: no limit).
    signing_opens_at: datetime | None
    signing_closes_at: datetime | None


class RunSheetResponse(BaseModel):
    """A day's run sheet: its sessions (a tab each) and its children."""

    date: date
    sessions: list[RunSheetSessionResponse]
    entries: list[RunSheetEntryResponse]
