from app.utils.auth import get_current_user
from app.schemas.inventory import InventoryUpdate
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.models.product import Product
from app.schemas.inventory import InventoryCreate, InventoryResponse

router = APIRouter()

# ==========================================
# ADD ITEM TO SHOP INVENTORY (Protected: Shop Owner Only)
# ==========================================
@router.post("/", response_model=InventoryResponse)
def add_to_inventory(
    item_data: InventoryCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Require Token
):
    # 1. Fetch the shop to verify ownership
    shop = db.query(Shop).filter(Shop.id == item_data.shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    # 2. The Master Lock: Is this THEIR shop?
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You can only manage inventory for your own shop."
        )

    # 3. Prevent duplicate entries
    existing = db.query(InventoryItem).filter(
        InventoryItem.shop_id == item_data.shop_id,
        InventoryItem.product_id == item_data.product_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product already in your inventory.")

    new_item = InventoryItem(**item_data.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("/shop/{shop_id}", response_model=List[InventoryResponse])
def get_shop_inventory(shop_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 1. Verify the shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    # 2. Fetch all inventory items linked to this specific shop_id
    inventory = db.query(InventoryItem).filter(InventoryItem.shop_id == shop_id).offset(skip).limit(limit).all()
    return inventory

# ==========================================
# UPDATE PRICE OR STOCK (Protected: Shop Owner Only)
# ==========================================
@router.patch("/{item_id}", response_model=InventoryResponse)
def update_inventory_item(
    item_id: int, 
    update_data: InventoryUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Require Token
):
    # 1. Find the inventory item
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # 2. Verify shop ownership
    shop = db.query(Shop).filter(Shop.id == item.shop_id).first()
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You cannot edit prices or stock for another shop."
        )

    # 3. Apply updates dynamically
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item