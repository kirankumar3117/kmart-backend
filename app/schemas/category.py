from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ShopCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class ShopCategoryResponse(ShopCategoryBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ShopCategoryListResponse(BaseModel):
    success: bool = True
    data: List[ShopCategoryResponse]
