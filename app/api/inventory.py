from app.utils.auth import get_current_user
from app.schemas.inventory import InventoryUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.models.product import Product
from app.models.user import User
from app.schemas.inventory import InventoryCreate, InventoryResponse, ShopItemResponse

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

# ==========================================
# GET MERCHANT'S OWN INVENTORY (Protected)
# ==========================================
@router.get("/merchant", response_model=List[ShopItemResponse])
def get_merchant_inventory(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Role-Based Check
    if current_user.role != "merchant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Merchant access required.")
        
    # 2. Derive shop from token
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found for this merchant account.")
        
    # 3. Fetch inventory WITH product details via standard JOIN
    results = (
        db.query(InventoryItem, Product)
        .join(Product, InventoryItem.product_id == Product.id)
        .filter(InventoryItem.shop_id == shop.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 4. Map the joined tuples to our rich Pydantic response schema
    response_items = []
    for inv, prod in results:
        response_items.append({
            "inventory_id": inv.id,
            "product_id": prod.id,
            "product_name": prod.name,
            # We don't join category here to save speed, the UI usually just needs the name/image
            "category": None, 
            "image_url": prod.image_url,
            "mrp": prod.mrp,
            "unit": getattr(prod, 'unit', None), # fallback
            "price": inv.price,
            "stock": inv.stock
        })
        
    return response_items




# ==========================================
# UPDATE PRICE OR STOCK (Protected: Shop Owner Only)
# ==========================================
@router.patch("/{item_id}", response_model=InventoryResponse)
def update_inventory_item(
    item_id: UUID, 
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