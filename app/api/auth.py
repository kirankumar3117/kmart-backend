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
    VerifyAgentRequest,
    SendOTPRequest,
    VerifyOTPRequest,
    VerifyResponse,
)
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.core.config import settings

router = APIRouter()

# In-memory OTP store (for development only — use Redis/DB in production)
_otp_store: dict[str, str] = {}


# ==========================================
# REGISTER NEW USER (existing endpoint)
# ==========================================
@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        email=user_data.email,
        hashed_password=hashed_pwd,
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ==========================================
# LOGIN (existing endpoint)
# ==========================================
@router.post("/login")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.phone_number == login_data.phone_number, User.role == login_data.role)
        .first()
    )

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number, password, or role",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


# ==========================================
# STEP 2a: VERIFY VIA AGENT CODE
# ==========================================
def _build_verify_response(shop: Shop) -> dict:
    """Helper: builds the standard verification response with tokens."""
    access_token = create_access_token(data={"sub": str(shop.id), "role": "shopkeeper"})
    refresh_token = create_refresh_token(data={"sub": str(shop.id), "role": "shopkeeper"})

    return {
        "success": True,
        "data": {
            "user": {
                "id": str(shop.id),
                "phone": shop.phone,
                "name": shop.owner_name,
                "role": "shopkeeper",
                "is_verified": shop.is_verified,
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
            },
            "onboarding_step": shop.onboarding_step.value,
        },
    }


@router.post("/verify-agent")
def verify_agent(body: VerifyAgentRequest, db: Session = Depends(get_db)):
    # 1. Look up shop by phone
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Please register first.")

    # 2. Validate agent code
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

    # 3. Mark shop as verified
    shop.is_verified = True
    shop.onboarding_step = OnboardingStep.VERIFIED
    shop.agent_id = agent.id

    db.commit()
    db.refresh(shop)

    return _build_verify_response(shop)


# ==========================================
# STEP 2b: SEND OTP (fallback)
# ==========================================
@router.post("/send-otp")
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    # Validate shop exists
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Please register first.")

    # Generate 4-digit OTP
    otp = str(random.randint(1000, 9999))
    _otp_store[body.phone] = otp

    # TODO: Integrate real SMS provider (Twilio / MSG91)
    print(f"📱 [DEV OTP] Phone: {body.phone} → OTP: {otp}")

    return {
        "success": True,
        "message": "OTP sent successfully",
        "dev_otp": otp,  # Remove in production!
    }


# ==========================================
# STEP 2c: VERIFY OTP (fallback)
# ==========================================
@router.post("/verify-otp")
def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    # 1. Look up shop
    shop = db.query(Shop).filter(Shop.phone == body.phone).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Please register first.")

    # 2. Validate OTP
    stored_otp = _otp_store.get(body.phone)
    if not stored_otp or stored_otp != body.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    # 3. Clear used OTP
    del _otp_store[body.phone]

    # 4. Mark shop as verified (same as agent-code flow)
    shop.is_verified = True
    shop.onboarding_step = OnboardingStep.VERIFIED

    db.commit()
    db.refresh(shop)

    return _build_verify_response(shop)