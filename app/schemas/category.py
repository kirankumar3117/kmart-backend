from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.schemas.product_category import ProductCategoryResponse

class ShopCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class ShopCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    product_category_ids: Optional[List[UUID]] = None

class ShopCategoryResponse(ShopCategoryBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    product_categories: List[ProductCategoryResponse] = []

    class Config:
        from_attributes = True

class ShopCategoryListResponse(BaseModel):
    success: bool = True
    data: List[ShopCategoryResponse]
