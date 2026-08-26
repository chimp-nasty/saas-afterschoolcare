from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.attendance_record import AttendanceRecord


class AttendanceRecordRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        booking_id: UUID,
        signed_in_at: datetime | None = None,
        signed_out_at: datetime | None = None,
        signed_in_by_user_id: UUID | None = None,
        signed_out_by_user_id: UUID | None = None,
    ) -> AttendanceRecord:
        record = AttendanceRecord(
            booking_id=booking_id,
            signed_in_at=signed_in_at,
            signed_out_at=signed_out_at,
            signed_in_by_user_id=signed_in_by_user_id,
            signed_out_by_user_id=signed_out_by_user_id,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> AttendanceRecord | None:
        return (
            self.db.query(AttendanceRecord)
            .filter(AttendanceRecord.id == id)
            .first()
        )
