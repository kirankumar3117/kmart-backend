from sqlalchemy import Column, Integer, String, Boolean, Enum
from app.db.base import Base
import enum

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    SHOPKEEPER = "SHOPKEEPER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True, nullable=False)
    
    # Phone number is now the primary required field
    phone_number = Column(String, unique=True, index=True, nullable=False)
    
    # Email is now completely optional
    email = Column(String, unique=True, index=True, nullable=True) 
    
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="customer")