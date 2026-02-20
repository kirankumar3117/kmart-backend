from pydantic import BaseModel
from typing import Optional

# Base Schema (Shared properties)
class ProductBase(BaseModel):
    name: str
    category: str
    image_url: Optional[str] = None
    mrp: float
    unit: str
    description: Optional[str] = None

# Schema for CREATING a product (Input)
class ProductCreate(ProductBase):
    barcode: Optional[str] = None

# Schema for READING a product (Output)
class ProductResponse(ProductBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True  # Allows reading from SQLAlchemy models