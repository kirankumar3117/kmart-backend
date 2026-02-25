from sqlalchemy import Column, Integer, String, Boolean, Text, Float, ForeignKey
from app.db.base import Base

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)

    address = Column(Text, nullable=False)

    is_active = Column(Boolean, default=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    