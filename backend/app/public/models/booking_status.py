from sqlalchemy import Boolean, Column, SmallInteger, String, Text

from app.db.base import Base


class BookingStatus(Base):
    __tablename__ = "booking_statuses"
    __table_args__ = {"schema": "public"}

    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    label = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
