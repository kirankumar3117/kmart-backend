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

@router.post("/", response_model=InventoryResponse)
def add_inventory_item(item: InventoryCreate, db: Session = Depends(get_db)):
    # 1. Verify the shop actually exists
    shop = db.query(Shop).filter(Shop.id == item.shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    # 2. Verify the product actually exists in the Master Catalog
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in master catalog")
        
    # 3. Check if this shop ALREADY added this exact product to their inventory
    existing_item = db.query(InventoryItem).filter(
        InventoryItem.shop_id == item.shop_id,
        InventoryItem.product_id == item.product_id
    ).first()
    
    if existing_item:
        raise HTTPException(status_code=400, detail="Product is already in this shop's inventory.")
        
    # 4. If all checks pass, add the item to the shop's inventory!
    db_inventory = InventoryItem(**item.model_dump())
    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    
    return db_inventory

@router.get("/shop/{shop_id}", response_model=List[InventoryResponse])
def get_shop_inventory(shop_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 1. Verify the shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    # 2. Fetch all inventory items linked to this specific shop_id
    inventory = db.query(InventoryItem).filter(InventoryItem.shop_id == shop_id).offset(skip).limit(limit).all()
    return inventory

@router.patch("/{item_id}", response_model=InventoryResponse)
def update_inventory(item_id: int, update_data: InventoryUpdate, db: Session = Depends(get_db)):
    # 1. Find the specific inventory item on the shelf
    inventory_item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
        
    # 2. Update only the fields that were provided in the request
    if update_data.price is not None:
        inventory_item.price = update_data.price
    if update_data.stock is not None:
        inventory_item.stock = update_data.stock
        
    # 3. Save the changes to the database
    db.commit()
    db.refresh(inventory_item)
    
    return inventory_item