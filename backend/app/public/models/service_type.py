from sqlalchemy import Boolean, Column, SmallInteger, String

from app.db.base import Base


class ServiceType(Base):
    __tablename__ = "service_types"
    __table_args__ = {"schema": "public"}

    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), nullable=False, unique=True)
    label = Column(String(64), nullable=False)

    stripe_product_id = Column(String(255), nullable=True)
    stripe_price_id = Column(String(255), nullable=True, unique=True)

    is_active = Column(Boolean, nullable=False, server_default="true")
