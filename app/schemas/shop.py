from pydantic import BaseModel
from typing import Optional

class ShopBase(BaseModel):
    name: str
    address: str
    is_active: bool
    latitude: float
    longitude: float

class ShopCreate(ShopBase):
    owner_id: int

class ShopResponse(ShopBase):
    id: int
    owner_id: int
    is_active: bool

    class Config:
        from_attributes = True