import random
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.shop import OnboardingStep
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.onboarding import CheckPhoneRequest, CheckPhoneResponse, CheckPhoneData
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

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    from app.core.security import verify_token
    token_data = verify_token(credentials.credentials)
    if not token_data or not token_data.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == token_data["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has been deactivated.")
        
    return user


# ==========================================
# 1. CHECK PHONE STATUS (Public)
# ==========================================
@router.post("/check-status")
def check_phone_status(body: CheckPhoneRequest, db: Session = Depends(get_db)):
    # check-status defaults to checking customer accounts
    user = db.query(User).filter(
        User.phone_number == body.phone,
        User.role == "customer"
    ).first()

    if not user:
        return CheckPhoneResponse(
            data=CheckPhoneData(status="new_user", phone=body.phone)
        )

    # In the simplified flow, all registered users are active.
    return CheckPhoneResponse(
        data=CheckPhoneData(
            status="active",
            shop_id=str(user.id),  # reusing shop_id field name for frontend compatibility
            shop_name=user.full_name,
            phone=user.phone_number,
        )
    )

# ==========================================
# HELPER: Build Auth Response with configurable Refresh Token duration
# ==========================================
def _build_auth_response(user: User, stay_logged_in: bool = False) -> dict:
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    
    # 30 days if remember me is checked, otherwise 1 day
    expires_days = 30 if stay_logged_in else 1
    refresh_token = create_refresh_token(data={"sub": str(user.id), "role": user.role}, expires_days=expires_days)

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
                "stay_logged_in": stay_logged_in
            },
            "onboarding_step": user.onboarding_step.value,
        },
    }

# ==========================================
# 2. REGISTER & LOGIN AUTOMATICALLY
# ==========================================
@router.post("/register")
def register_user(body: UserCreate, db: Session = Depends(get_db)):
    role_to_check = body.role or "customer"
    existing = db.query(User).filter(
        User.phone_number == body.phone_number,
        User.role == role_to_check
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered. Please log in.",
        )
        
    hashed_pwd = get_password_hash(body.password)

    # Instantly verify the user and issue tokens
    new_user = User(
        full_name=body.full_name,
        phone_number=body.phone_number,
        email=body.email,
        hashed_password=hashed_pwd,
        role=body.role or "customer",
        is_verified=True,
        onboarding_step=OnboardingStep.COMPLETED,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return _build_auth_response(new_user, stay_logged_in=body.stay_logged_in)


# ==========================================
# 3. DIRECT PASSWORD LOGIN
# ==========================================
@router.post("/login")
def login_user(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == body.phone_number, User.role == body.role).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )
    
    if user.hashed_password and verify_password(body.password, user.hashed_password):
        pass # Success
    elif user.hashed_pin and verify_password(body.password, user.hashed_pin):
        pass # Success (fallback to support older users)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )

    # Returning token payload with flexible expiration
    return _build_auth_response(user, stay_logged_in=body.stay_logged_in)

