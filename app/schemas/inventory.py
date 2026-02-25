from pydantic import BaseModel

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