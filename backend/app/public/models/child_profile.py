import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ChildProfile(Base):
    __tablename__ = "child_profile"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenancy.locations.id"),
        nullable=False,
    )

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    dob = Column(Date, nullable=False)

    has_medical_condition = Column(Boolean, nullable=False, server_default="false")
    medical_info = Column(Text, nullable=True)

    has_allergies = Column(Boolean, nullable=False, server_default="false")
    allergy_info = Column(Text, nullable=True)

    requires_medication = Column(Boolean, nullable=False, server_default="false")
    medication_info = Column(Text, nullable=True)

    medical_documentation_provided = Column(Boolean, nullable=False, server_default="false")
    medical_review_required = Column(Boolean, nullable=False, server_default="false")

    medical_review_status_id = Column(
        SmallInteger,
        ForeignKey("public.medical_review_statuses.id"),
        nullable=True,
    )

    care_details_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
