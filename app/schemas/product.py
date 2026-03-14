from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.schemas.product_category import ProductCategoryResponse


# ==========================================
# PRODUCT SCHEMAS
# ==========================================

# Schema for CREATING a product (Input)
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    mrp: float
    unit: str
    barcode: Optional[str] = None
    category_ids: List[int]  # At least one required

    @field_validator("category_ids")
    @classmethod
    def category_ids_not_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Product must belong to at least one category")
        return v


# Schema for UPDATING a product (all optional)
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    mrp: Optional[float] = None
    unit: Optional[str] = None
    barcode: Optional[str] = None
    is_active: Optional[bool] = None
    category_ids: Optional[List[int]] = None

    @field_validator("category_ids")
    @classmethod
    def category_ids_not_empty(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("Product must belong to at least one category")
        return v


# Schema for READING a product (Output)
class ProductResponse(BaseModel):
    id: int
    merchant_id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    mrp: float
    unit: Optional[str] = None
    barcode: Optional[str] = None
    is_active: bool
    is_deleted: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    categories: List[ProductCategoryResponse] = []

    class Config:
        from_attributes = True