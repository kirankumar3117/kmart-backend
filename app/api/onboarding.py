import os
import uuid
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.shop import Shop, OnboardingStep
from app.utils.shop_auth import get_current_shop
from app.schemas.onboarding import (
    ShopRegisterRequest,
    ShopRegisterResponse,
    ShopRegisterData,
    ShopSetupResponse,
    ShopSetupData,
    OnboardingStatusResponse,
    OnboardingStatusData,
)

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==========================================
# STEP 1: REGISTER SHOP (Public — no auth)
# ==========================================
@router.post("/register")
def register_shop(body: ShopRegisterRequest, db: Session = Depends(get_db)):
    # Check if phone already exists
    existing = db.query(Shop).filter(Shop.phone == body.phone).first()

    if existing:
        # Already fully onboarded → error
        if existing.onboarding_step == OnboardingStep.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already registered. Please login.",
            )

        # Incomplete onboarding → return current progress so mobile app can resume
        return ShopRegisterResponse(
            data=ShopRegisterData(
                shop_id=str(existing.id),
                phone=existing.phone,
                onboarding_step=existing.onboarding_step.value,
            )
        )

    # Create a brand-new shop record (Step 1 done)
    new_shop = Shop(
        shop_name=body.shop_name,
        owner_name=body.owner_name,
        phone=body.phone,
        email=body.email,
        referral_code=body.referral_code,
        onboarding_step=OnboardingStep.REGISTERED,
    )
    db.add(new_shop)
    db.commit()
    db.refresh(new_shop)

    return ShopRegisterResponse(
        data=ShopRegisterData(
            shop_id=str(new_shop.id),
            phone=new_shop.phone,
            onboarding_step=new_shop.onboarding_step.value,
        )
    )


# ==========================================
# STEP 3: SHOP SETUP (Authenticated — Bearer token)
# ==========================================
@router.post("/setup")
def shop_setup(
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    shop_image: UploadFile = File(None),
    owner_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_shop: Shop = Depends(get_current_shop),
):
    # Validate file types and sizes
    max_size = 5 * 1024 * 1024  # 5MB

    shop_image_url = None
    owner_image_url = None

    if shop_image and shop_image.filename:
        if not shop_image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="shop_image must be JPEG or PNG")
        content = shop_image.file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="shop_image exceeds 5MB limit")
        ext = shop_image.filename.split(".")[-1]
        filename = f"shop_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(content)
        shop_image_url = f"/static/{filename}"

    if owner_image and owner_image.filename:
        if not owner_image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="owner_image must be JPEG or PNG")
        content = owner_image.file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="owner_image exceeds 5MB limit")
        ext = owner_image.filename.split(".")[-1]
        filename = f"owner_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(content)
        owner_image_url = f"/static/{filename}"

    # Update shop record
    current_shop.latitude = latitude
    current_shop.longitude = longitude
    current_shop.address = address
    if shop_image_url:
        current_shop.shop_image_url = shop_image_url
    if owner_image_url:
        current_shop.owner_image_url = owner_image_url
    current_shop.onboarding_step = OnboardingStep.COMPLETED
    current_shop.is_onboarded = True

    db.commit()
    db.refresh(current_shop)

    return ShopSetupResponse(
        data=ShopSetupData(
            shop_id=str(current_shop.id),
            name=current_shop.shop_name,
            address=current_shop.address,
            shop_image_url=current_shop.shop_image_url,
            owner_image_url=current_shop.owner_image_url,
            is_onboarded=current_shop.is_onboarded,
            onboarding_step=current_shop.onboarding_step.value,
        )
    )


# ==========================================
# ONBOARDING STATUS CHECK (Authenticated)
# ==========================================
@router.get("/me/onboarding-status")
def get_onboarding_status(current_shop: Shop = Depends(get_current_shop)):
    return OnboardingStatusResponse(
        data=OnboardingStatusData(
            onboarding_step=current_shop.onboarding_step.value,
            is_onboarded=current_shop.is_onboarded,
        )
    )
