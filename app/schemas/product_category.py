from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ==========================================
# PRODUCT CATEGORY SCHEMAS
# ==========================================
class ProductCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductCategoryResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    is_deleted: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
