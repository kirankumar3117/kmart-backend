import random
import re

from app.schemas.user import UserLogin
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.shop import Shop, OnboardingStep
from app.models.agent import Agent
from app.schemas.user import UserCreate, UserResponse
from app.schemas.onboarding import (
    CheckPhoneRequest,
    CheckPhoneResponse,
    CheckPhoneData,
    LoginPinRequest,
    VerifyAgentRequest,
    SendOTPRequest,
    VerifyOTPRequest,
    SetPinRequest,
    SetPinResponse,
    SetPinData,
)
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.core.config import settings
from app.utils.shop_auth import get_current_shop

router = APIRouter()

# In-memory OTP store (for development only — use Redis/DB in production)
_otp_store: dict[str, str] = {}


# ==========================================
# CHECK PHONE STATUS (Public — no auth)
# Returns the status string the frontend uses to route to the right screen:
#   new_user   → [register screen]
#   registered → [verify screen]
#   verified   → [set-pin screen]
#   pin_set    → [shop-setup screen]
#   active     → [login/home screen]
# ==========================================
@router.post("/check-status")
def check_phone_status(body: CheckPhoneRequest, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()

    if not shop:
        return CheckPhoneResponse(
            data=CheckPhoneData(status="new_user", phone=body.phone)
        )

    # Map OnboardingStep enum → frontend status string
    step_to_status = {
        OnboardingStep.REGISTERED: "registered",
        OnboardingStep.VERIFIED: "verified",
        OnboardingStep.PIN_SET: "pin_set",
        OnboardingStep.COMPLETED: "active",
    }
    user_status = step_to_status.get(shop.onboarding_step, "registered")

    return CheckPhoneResponse(
        data=CheckPhoneData(
            status=user_status,
            shop_id=str(shop.id),
            shop_name=shop.shop_name,
            phone=shop.phone,
        )
    )


# ==========================================
# LOGIN WITH PIN (for returning users)
# ==========================================
@router.post("/login-pin")
def login_pin(body: LoginPinRequest, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()

    if not shop or not shop.hashed_pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or PIN",
        )

    if not verify_password(body.pin, shop.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect PIN",
        )

    return _build_verify_response(shop)


# ==========================================
# REGISTER NEW USER (existing endpoint — legacy, kept for compatibility)
# ==========================================
@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Treat empty string or whitespace email as None
    email_val = user_data.email.strip() if user_data.email and user_data.email.strip() else None

    if email_val:
        existing_email = db.query(User).filter(User.email == email_val).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        email=email_val,
        hashed_password=hashed_pwd,
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ==========================================
# LOGIN (existing endpoint — legacy)
# ==========================================
@router.post("/login")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.phone_number == login_data.phone_number, User.role == login_data.role)
        .first()
    )

    if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number, password, or role",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


# ==========================================
# HELPER: Build standard verification response
# Used by: verify-otp, verify-agent, login-pin
# ==========================================
def _build_verify_response(shop: Shop) -> dict:
    """Helper: builds the standard verification response with tokens."""
    access_token = create_access_token(data={"sub": str(shop.id), "role": "merchant"})
    refresh_token = create_refresh_token(data={"sub": str(shop.id), "role": "merchant"})

    return {
        "success": True,
        "data": {
            "user": {
                "id": str(shop.id),
                "phone": shop.phone,
                "name": shop.owner_name,
                "email": shop.email,
                "role": "merchant",
                "isVerified": shop.is_verified,   # camelCase — matches frontend expectation
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
            "onboarding_step": shop.onboarding_step.value,
        },
    }


# ==========================================
# VERIFY VIA AGENT CODE (Public — no auth)
# ==========================================
@router.post("/verify-agent")
def verify_agent(body: VerifyAgentRequest, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Please register first.")

    agent = (
        db.query(Agent)
        .filter(Agent.agent_code == body.agent_code, Agent.is_active == True)
        .first()
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive agent code",
        )

    shop.is_verified = True
    shop.onboarding_step = OnboardingStep.VERIFIED
    shop.agent_id = agent.id

    db.commit()
    db.refresh(shop)

    return _build_verify_response(shop)


# ==========================================
# SEND OTP (Public — no auth)
# Called automatically after /shops/register and by the Resend button
# ==========================================
@router.post("/send-otp")
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Please register first.")

    otp = str(random.randint(1000, 9999))
    _otp_store[body.phone] = otp

    # TODO: Integrate real SMS provider (Twilio / MSG91)
    print(f"📱 [DEV OTP] Phone: {body.phone} → OTP: {otp}")

    return {
        "success": True,
        "data": {
            "message": "OTP sent successfully",
            "dev_otp": otp,   # Remove in production!
        },
    }


# ==========================================
# VERIFY OTP (Public — no auth)
# ==========================================
@router.post("/verify-otp")
def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Please register first.")

    stored_otp = _otp_store.get(body.phone)
    if not stored_otp or stored_otp != body.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    del _otp_store[body.phone]

    shop.is_verified = True
    shop.onboarding_step = OnboardingStep.VERIFIED

    db.commit()
    db.refresh(shop)

    return _build_verify_response(shop)


# ==========================================
# SET PIN (Authenticated — Bearer token required)
# Step 3 of the onboarding flow: sets and hashes the 4-digit PIN
# ==========================================
@router.post("/set-pin")
def set_pin(
    body: SetPinRequest,
    db: Session = Depends(get_db),
    current_shop: Shop = Depends(get_current_shop),
):
    if not current_shop.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your phone number before setting a PIN",
        )

    current_shop.hashed_pin = get_password_hash(body.pin)
    current_shop.onboarding_step = OnboardingStep.PIN_SET

    db.commit()
    db.refresh(current_shop)

    return SetPinResponse(
        data=SetPinData(
            message="PIN set successfully",
            onboarding_step=current_shop.onboarding_step.value,
        )
    )