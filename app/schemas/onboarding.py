from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


# ==========================================
# STEP 1: REGISTER SHOP
# ==========================================
class ShopRegisterRequest(BaseModel):
    shop_name: str = Field(..., min_length=3, description="Shop name (min 3 chars)")
    owner_name: str = Field(..., min_length=3, description="Owner name (min 3 chars)")
    phone: str = Field(..., description="10-digit phone number")
    email: Optional[str] = None
    referral_code: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return cleaned


class ShopRegisterData(BaseModel):
    shop_id: str
    phone: str
    onboarding_step: str

    class Config:
        from_attributes = True


class ShopRegisterResponse(BaseModel):
    success: bool = True
    data: ShopRegisterData


# ==========================================
# STEP 2: VERIFY (Agent Code / OTP)
# ==========================================
class VerifyAgentRequest(BaseModel):
    phone: str
    agent_code: str


class SendOTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return cleaned


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=4, max_length=4)


class VerifyUserData(BaseModel):
    id: str
    phone: str
    name: str
    role: str = "shopkeeper"
    is_verified: bool


class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class VerifyResponse(BaseModel):
    success: bool = True
    data: dict  # contains user, tokens, onboarding_step


# ==========================================
# STEP 3: SHOP SETUP
# ==========================================
class ShopSetupData(BaseModel):
    shop_id: str
    name: str
    address: str
    shop_image_url: Optional[str] = None
    owner_image_url: Optional[str] = None
    is_onboarded: bool
    onboarding_step: str

    class Config:
        from_attributes = True


class ShopSetupResponse(BaseModel):
    success: bool = True
    data: ShopSetupData


# ==========================================
# ONBOARDING STATUS
# ==========================================
class OnboardingStatusData(BaseModel):
    onboarding_step: str
    is_onboarded: bool

    class Config:
        from_attributes = True


class OnboardingStatusResponse(BaseModel):
    success: bool = True
    data: OnboardingStatusData
