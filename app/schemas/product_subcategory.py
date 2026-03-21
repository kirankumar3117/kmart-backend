from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


# ==========================================
# PRODUCT SUBCATEGORY SCHEMAS
# ==========================================
class ProductSubcategoryCreate(BaseModel):
    name: str
    category_id: UUID
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductSubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductSubcategoryResponse(BaseModel):
    id: UUID
    category_id: UUID
    category_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    is_deleted: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
