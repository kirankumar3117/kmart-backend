from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum
from app.db.base import Base
from app.models.shop import OnboardingStep
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
    
    hashed_password = Column(String, nullable=True) # made optional for PIN auth
    is_active = Column(Boolean, default=True)
    role = Column(String, default="customer")

    # Features for progressive onboarding
    is_verified = Column(Boolean, default=False)
    hashed_pin = Column(String, nullable=True)
    onboarding_step = Column(
        SQLEnum(OnboardingStep, name="user_onboarding_step_enum", create_constraint=True),
        default=OnboardingStep.REGISTERED,
        nullable=False,
    )