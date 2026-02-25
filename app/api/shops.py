from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.shop import Shop
from app.models.user import User
from app.schemas.shop import ShopCreate, ShopResponse

router = APIRouter()

@router.post("/", response_model=ShopResponse)
def create_shop(shop: ShopCreate, db: Session = Depends(get_db)):
    # 1. Verify the user (owner) actually exists in our database
    owner = db.query(User).filter(User.id == shop.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # 2. Create the shop object using the payload from the frontend
    db_shop = Shop(**shop.model_dump())
    
    # 3. Save it to the Docker PostgreSQL database
    db.add(db_shop)
    db.commit()
    db.refresh(db_shop)
    
    return db_shop

@router.get("/", response_model=List[ShopResponse])
def get_shops(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Fetch a list of all active shops (with basic pagination)
    shops = db.query(Shop).filter(Shop.is_active == True).offset(skip).limit(limit).all()
    return shops