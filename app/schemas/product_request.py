from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ==========================================
# MERCHANT: Submit a product request
# ==========================================
class ProductRequestCreate(BaseModel):
    name: str
    image_url: Optional[str] = None
    price: float
    stock: int = 0


# ==========================================
# RESPONSE: What comes back from the API
# ==========================================
class ProductRequestResponse(BaseModel):
    id: UUID
    merchant_user_id: UUID
    shop_id: UUID
    name: str
    image_url: Optional[str] = None
    price: float
    stock: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# ADMIN: Product payload when accepting
# ==========================================
class AdminProductPayload(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    mrp: float
    unit: str
    barcode: Optional[str] = None
    category_ids: List[UUID]
    subcategory_id: Optional[UUID] = None


# ==========================================
# ADMIN: Review action (accept / reject)
# ==========================================
class AdminReviewPayload(BaseModel):
    action: str  # "accept" or "reject"
    product_payload: Optional[AdminProductPayload] = None
