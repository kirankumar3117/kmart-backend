from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


# ==========================================
# CHECK PHONE STATUS
# ==========================================
class CheckPhoneRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return cleaned


class CheckPhoneData(BaseModel):
    # "new_user" | "registered" | "verified" | "pin_set" | "active"
    status: str
    shop_id: Optional[str] = None
    shop_name: Optional[str] = None
    phone: str


class CheckPhoneResponse(BaseModel):
    success: bool = True
    data: CheckPhoneData


# ==========================================
# STEP 1: REGISTER SHOP (Public — no auth, no PIN)
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
# LOGIN WITH PIN
# ==========================================
class LoginPinRequest(BaseModel):
    phone: str
    pin: str = Field(..., min_length=4, max_length=4)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return cleaned


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


class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class VerifyUserData(BaseModel):
    id: str
    phone: str
    name: str
    email: Optional[str] = None
    role: str = "shopkeeper"
    isVerified: bool  # camelCase to match frontend expectation


class VerifyResponse(BaseModel):
    success: bool = True
    data: dict  # contains user, tokens, onboarding_step


# ==========================================
# STEP 3: SET PIN (Authenticated — Bearer token)
# ==========================================
class SetPinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4, description="4-digit numeric PIN")

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("PIN must contain only digits")
        return v


class SetPinData(BaseModel):
    message: str
    onboarding_step: str


class SetPinResponse(BaseModel):
    success: bool = True
    data: SetPinData


# ==========================================
# STEP 4: SHOP SETUP (Authenticated — Bearer token)
# ==========================================
class ShopSetupData(BaseModel):
    id: str
    shop_name: str
    owner_name: str
    phone: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shop_image_url: Optional[str] = None
    owner_image_url: Optional[str] = None
    is_online: bool
    is_verified: bool
    is_onboarded: bool
    onboarding_step: str
    created_at: Optional[str] = None

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
