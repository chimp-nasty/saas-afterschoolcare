import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, Text, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ChildProfile(Base):
    __tablename__ = "child_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenancy.locations.id"),
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    dob = Column(Date, nullable=False)

    medical_info = Column(Text, nullable=True)
    allergy_info = Column(Text, nullable=True)
    medication_info = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "location_id",
            "first_name",
            "last_name",
            "dob",
            "is_active",
            name="uq_child_profiles_user_name_dob",
        ),
        {"schema": "public"},
    )
