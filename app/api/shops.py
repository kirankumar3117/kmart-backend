from app.utils.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.shop import Shop
from app.models.user import User
from app.schemas.shop import ShopCreate, ShopResponse

router = APIRouter()

# ==========================================
# CREATE A SHOP (Protected: Shopkeepers Only)
# ==========================================
@router.post("/", response_model=ShopResponse)
def create_shop(
    shop: ShopCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Security Token
):
    # 1. Verify they are actually a shopkeeper
    if current_user.role != "shopkeeper":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only shopkeepers can register a new shop."
        )

    # 2. Mash the frontend data and the secure token ID together
    # **shop.model_dump() unpacks the JSON body (name, category, etc.)
    db_shop = Shop(**shop.model_dump(), owner_id=current_user.id)
    
    # 3. Save to Postgres
    db.add(db_shop)
    db.commit()
    db.refresh(db_shop)
    
    return db_shop

# ==========================================
# GET ALL SHOPS (Public: Customers need to see shops!)
# ==========================================
@router.get("/", response_model=List[ShopResponse])
def get_shops(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    shops = db.query(Shop).offset(skip).limit(limit).all()
    return shops