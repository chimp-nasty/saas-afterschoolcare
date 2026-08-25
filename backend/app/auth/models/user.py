import uuid

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    terms_accepted_at = Column(DateTime(timezone=True), nullable=False)
    terms_version = Column(String(50), nullable=False, server_default="v1")

    is_active = Column(Boolean, nullable=False, server_default="false")

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_login = Column(DateTime(timezone=True), nullable=True)
