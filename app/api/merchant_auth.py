from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.shop import Shop, OnboardingStep
from app.models.shop_category import ShopCategory
from app.schemas.merchant_auth import MerchantRegisterRequest, MerchantLoginRequest
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings

router = APIRouter()

# ==========================================
# HELPER: Build Auth Response with configurable Refresh Token duration
# ==========================================
def _build_auth_response(user: User, shop: Shop, stay_logged_in: bool = False) -> dict:
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    
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
            "shop": {
                "id": str(shop.id),
                "shop_name": shop.shop_name,
                "onboarding_step": shop.onboarding_step.value
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "stay_logged_in": stay_logged_in
            }
        },
    }

# ==========================================
# 1. REGISTER & LOGIN AUTOMATICALLY (Self-Registration)
# ==========================================
@router.post("/register")
def register_merchant(request: MerchantRegisterRequest, db: Session = Depends(get_db)):
    # 1. Validate Shop Category
    category_record = db.query(ShopCategory).filter(ShopCategory.id == request.shop_category_id).first()
    if not category_record:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shop category ID"
        )

    # 2. Check if User/Merchant phone already exists
    existing_user = db.query(User).filter(
        User.phone_number == request.phone_number,
        User.role == "merchant"
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered. Please log in."
        )

    # 3. Check if Shop phone already exists
    existing_shop = db.query(Shop).filter(Shop.phone == request.phone_number).first()
    if existing_shop:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shop with this phone number already exists. Please log in."
        )

    if request.email:
        existing_user_email = db.query(User).filter(
            User.email == request.email,
            User.role == "merchant"
        ).first()
        if existing_user_email:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists as a merchant"
            )

    # 4. Hash the strong Password
    hashed_pwd = get_password_hash(request.password)

    # 5. Create the Merchant User
    new_user = User(
        full_name=request.merchant_name,
        phone_number=request.phone_number,
        email=request.email,
        hashed_password=hashed_pwd,
        role="merchant",  
        onboarding_step=OnboardingStep.COMPLETED,
        is_verified=True # Self-registered is instantly verified in this simplified flow
    )
    db.add(new_user)
    db.flush() # Get the new_user.id without committing

    # 6. Create the full Shop profile
    new_shop = Shop(
        owner_id=new_user.id,
        category_id=category_record.id,
        shop_name=request.shop_name,
        owner_name=request.merchant_name,
        phone=request.phone_number,
        email=request.email,
        address=request.shop_location,
        shop_image_url=request.shop_image_url,
        owner_image_url=request.merchant_image_url,
        # Self-registration implies no agent
        onboarded_by_agent_id=None,
        agent_id=None,
        is_verified=True,
        is_onboarded=True,
        onboarding_step=OnboardingStep.COMPLETED,
    )
    db.add(new_shop)

    # 7. Commit
    db.commit()
    db.refresh(new_user)
    db.refresh(new_shop)

    return _build_auth_response(new_user, new_shop, stay_logged_in=request.stay_logged_in)


# ==========================================
# 2. DIRECT LOGIN FOR MERCHANTS
# ==========================================
@router.post("/login")
def login_merchant(body: MerchantLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == body.phone_number, User.role == "merchant").first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )
    
    # Authenticate: Checks password, or falls back to PIN (for legacy or agent-onboarded merchants)
    if user.hashed_password and verify_password(body.password, user.hashed_password):
        pass # Success
    elif user.hashed_pin and verify_password(body.password, user.hashed_pin):
        pass # Success (fallback)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )

    # Get the shop to include in the response payload
    shop = db.query(Shop).filter(Shop.owner_id == user.id).first()

    return _build_auth_response(user, shop, stay_logged_in=body.stay_logged_in)
