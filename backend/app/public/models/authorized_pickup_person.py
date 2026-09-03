import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AuthorizedPickupPerson(Base):
    __tablename__ = "authorized_pickup_persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.child_profile.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)

    relation = Column(String(100), nullable=False)

    consent_confirmed = Column(Boolean, nullable=True)

    identity_verified_at = Column(DateTime(timezone=True), nullable=True)

    identity_verified_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )

    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "child_id",
            "phone",
            name="uq_authorized_pickup_person",
        ),
        {"schema": "public"},
    )
