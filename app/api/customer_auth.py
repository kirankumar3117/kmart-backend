import random
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.shop import OnboardingStep
from app.schemas.user import UserCreate, UserResponse
from app.schemas.onboarding import (
    CheckPhoneRequest,
    CheckPhoneResponse,
    CheckPhoneData,
    LoginPinRequest,
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
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

# In-memory OTP store (for development only — use Redis/DB in production)
_otp_store: dict[str, str] = {}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    from app.core.security import verify_token
    token_data = verify_token(credentials.credentials)
    if not token_data or not token_data.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == int(token_data["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ==========================================
# 1. CHECK PHONE STATUS (Public)
# ==========================================
@router.post("/check-status")
def check_phone_status(body: CheckPhoneRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == body.phone).first()

    if not user:
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
    user_status = step_to_status.get(user.onboarding_step, "registered")

    # If they are mostly done but we want to treat them as active
    if user_status == "pin_set":
        user_status = "active"

    return CheckPhoneResponse(
        data=CheckPhoneData(
            status=user_status,
            shop_id=str(user.id),  # reusing shop_id field name for frontend compatibility
            shop_name=user.full_name,
            phone=user.phone_number,
        )
    )


# ==========================================
# 2. REGISTER BASIC DETAILS (Step 1)
# ==========================================
@router.post("/register")
def register_user(body: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone_number == body.phone_number).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered. Please login.",
        )
        
    hashed_pwd = get_password_hash(body.password) if body.password else None

    # Create a brand-new user record (Step 1 done)
    new_user = User(
        full_name=body.full_name,
        phone_number=body.phone_number,
        email=body.email,
        hashed_password=hashed_pwd,
        role=body.role or "customer",
        onboarding_step=OnboardingStep.REGISTERED,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"success": True, "data": {"user_id": new_user.id, "phone": new_user.phone_number, "onboarding_step": new_user.onboarding_step.value}}


# ==========================================
# 3. SEND OTP (Public)
# ==========================================
@router.post("/send-otp")
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == body.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    otp = str(random.randint(1000, 9999))
    _otp_store[body.phone] = otp

    print(f"📱 [DEV OTP - CUSTOMER] Phone: {body.phone} → OTP: {otp}")

    return {
        "success": True,
        "data": {
            "message": "OTP sent successfully",
            "dev_otp": otp,  
        },
    }


# ==========================================
# HELPER: Build User verify response 
# ==========================================
def _build_verify_response(user: User) -> dict:
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "role": user.role})

    return {
        "success": True,
        "data": {
            "user": {
                "id": str(user.id),
                "phone": user.phone_number,
                "name": user.full_name,
                "email": user.email,
                "role": user.role,
                "isVerified": user.is_verified, 
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
            "onboarding_step": user.onboarding_step.value,
        },
    }

# ==========================================
# 4. VERIFY OTP (Public)
# ==========================================
@router.post("/verify-otp")
def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == body.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    stored_otp = _otp_store.get(body.phone)
    if not stored_otp or stored_otp != body.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    del _otp_store[body.phone]

    user.is_verified = True
    user.onboarding_step = OnboardingStep.VERIFIED

    db.commit()
    db.refresh(user)

    return _build_verify_response(user)


# ==========================================
# 5. SET PIN (Authenticated)
# ==========================================
@router.post("/set-pin")
def set_pin(
    body: SetPinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your phone number before setting a PIN",
        )

    current_user.hashed_pin = get_password_hash(body.pin)
    current_user.onboarding_step = OnboardingStep.PIN_SET

    db.commit()
    db.refresh(current_user)

    return SetPinResponse(
        data=SetPinData(
            message="PIN set successfully",
            onboarding_step=current_user.onboarding_step.value,
        )
    )

# ==========================================
# 6. LOGIN WITH PIN (For returning users)
# ==========================================
@router.post("/login-pin")
def login_pin(body: LoginPinRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == body.phone).first()

    if not user or not user.hashed_pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or PIN",
        )

    if not verify_password(body.pin, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect PIN",
        )

    return _build_verify_response(user)
