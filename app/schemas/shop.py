from pydantic import BaseModel
from typing import Optional

class ShopBase(BaseModel):
    name: str
    category: str
    address: str  # Made strictly required to match DB nullable=False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = True

class ShopCreate(ShopBase):
    # We purposely do NOT put owner_id here. 
    # The frontend shouldn't send it; the backend token will provide it!
    pass 

class ShopResponse(ShopBase):
    id: int
    owner_id: int # The frontend gets to see who owns it in the response

    class Config:
        from_attributes = True