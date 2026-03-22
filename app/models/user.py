import uuid
import enum
from sqlalchemy import Column, String, Boolean, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.models.shop import OnboardingStep

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    MERCHANT = "MERCHANT"
    AGENT = "AGENT"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    full_name = Column(String, index=True, nullable=False)
    
    # Phone number is required, uniqueness is now handled by composite constraint
    phone_number = Column(String, index=True, nullable=False)
    
    # Email is optional, uniqueness also handled by composite constraint
    email = Column(String, index=True, nullable=True) 
    
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
    
    # Push Notifications
    fcm_token = Column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('phone_number', 'role', name='uq_user_phone_role'),
        UniqueConstraint('email', 'role', name='uq_user_email_role'),
    )