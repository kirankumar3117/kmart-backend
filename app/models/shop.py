import uuid
import enum
from sqlalchemy import Column, String, Boolean, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class OnboardingStep(str, enum.Enum):
    REGISTERED = "registered"
    VERIFIED = "verified"
    COMPLETED = "completed"


class Shop(Base):
    __tablename__ = "shops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    shop_name = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    referral_code = Column(String, nullable=True)

    # Linked to the agent who verified this shop
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)

    # Location & images (filled in Step 3)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    shop_image_url = Column(String, nullable=True)
    owner_image_url = Column(String, nullable=True)

    # Status flags
    is_verified = Column(Boolean, default=False)
    is_onboarded = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)

    # Onboarding progress tracking
    onboarding_step = Column(
        Enum(OnboardingStep, name="onboarding_step_enum", create_constraint=True),
        default=OnboardingStep.REGISTERED,
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )