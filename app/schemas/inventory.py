from pydantic import BaseModel
from typing import Optional

# 1. The core fields we always need
class InventoryBase(BaseModel):
    price: float
    stock: int

# 2. What the frontend sends when adding an item to the store
class InventoryCreate(InventoryBase):
    shop_id: int
    product_id: int

# 3. What we send back to the frontend
class InventoryResponse(InventoryBase):
    id: int
    shop_id: int
    product_id: int

    class Config:
        from_attributes = True

# 4. What the frontend sends when updating (everything is optional)
class InventoryUpdate(BaseModel):
    price: Optional[float] = None
    stock: Optional[int] = None

# 5. Joined response: Product details + shop-specific price/stock
#    Used by GET /shops/{shop_id}/items
class ShopItemResponse(BaseModel):
    inventory_id: int       # InventoryItem.id
    product_id: int
    product_name: str
    category: Optional[str] = None
    image_url: Optional[str] = None
    mrp: float              # Max Retail Price (from master catalog)
    unit: Optional[str] = None
    price: float            # This shop's selling price
    stock: int              # This shop's current stock
    class Config:
        from_attributes = True