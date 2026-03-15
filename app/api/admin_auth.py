from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.user import User
from typing import Optional
from app.models.shop import OnboardingStep
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings

router = APIRouter()

class AdminRegisterRequest(BaseModel):
    name: str = Field(..., description="Full Name of the Admin")
    phone: str = Field(..., description="Phone number")
    password: str = Field(..., description="Strong password")
    email: Optional[str] = None
    secret_key: str = Field(..., description="The highly sensitive environment secret required to create an Admin")

class AdminLoginRequest(BaseModel):
    login_id: str = Field(..., description="Phone number or Email")
    password: str
    stay_logged_in: bool = False

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_admin(body: AdminRegisterRequest, db: Session = Depends(get_db)):
    # 1. VERIFY SECRET KEY
    if body.secret_key != settings.ADMIN_CREATION_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Admin Creation Secret Key."
        )

    # 2. CHECK IF PHONE/EMAIL EXISTS FOR ADMIN ROLE
    existing_phone = db.query(User).filter(User.phone_number == body.phone, User.role == "admin").first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An Admin with this phone number already exists."
        )

    if body.email:
        existing_email = db.query(User).filter(User.email == body.email, User.role == "admin").first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An Admin with this email already exists."
            )

    # 3. CREATE ADMIN
    hashed_pwd = get_password_hash(body.password)
    new_admin = User(
        full_name=body.name,
        phone_number=body.phone,
        email=body.email if body.email else None,
        hashed_password=hashed_pwd,
        role="admin",
        is_verified=True,
        onboarding_step=OnboardingStep.COMPLETED,
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    # 4. ISSUE TOKENS
    access_token = create_access_token(data={"sub": str(new_admin.id), "role": new_admin.role})
    refresh_token = create_refresh_token(data={"sub": str(new_admin.id), "role": new_admin.role}, expires_days=1)

    return {
        "success": True,
        "message": "Admin user successfully created.",
        "data": {
            "user": {
                "id": str(new_admin.id),
                "phone": new_admin.phone_number,
                "name": new_admin.full_name,
                "email": new_admin.email,
                "role": new_admin.role,
                "isVerified": new_admin.is_verified, 
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "stay_logged_in": False
            }
        },
    }

@router.post("/login")
def login_admin(body: AdminLoginRequest, db: Session = Depends(get_db)):
    # Admin can login with phone or email
    user = db.query(User).filter(
        ((User.phone_number == body.login_id) | (User.email == body.login_id)),
        User.role == "admin"
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login ID or password",
        )
    
    # Authenticate: Checks password
    if not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login ID or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your admin account has been deactivated."
        )

    # Build response payload
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    expires_days = 30 if body.stay_logged_in else 1
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
                "stay_logged_in": body.stay_logged_in
            }
        },
    }
