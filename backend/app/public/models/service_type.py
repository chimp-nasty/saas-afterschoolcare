from sqlalchemy import Column, SmallInteger, String

from app.db.base import Base


class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(SmallInteger, primary_key=True, autoincrement=True)

    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)

    __table_args__ = (
        {"schema": "public"},
    )
