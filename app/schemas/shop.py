from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.schemas.category import ShopCategoryResponse
from app.schemas.product_category import ProductCategoryResponse


class ShopBase(BaseModel):
    shop_name: str
    owner_name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ShopCreate(ShopBase):
    pass


class ShopUpdate(BaseModel):
    shop_name: Optional[str] = None
    address: Optional[str] = None
    category_id: Optional[UUID] = None  # To change Shop Type (Admin Only)
    product_category_ids: Optional[List[UUID]] = None  # To change what this specific shop sells
    is_online: Optional[bool] = None


class ShopResponse(ShopBase):
    id: UUID
    phone: str
    is_verified: bool = False
    is_onboarded: bool = False
    is_online: bool = False
    onboarding_step: str = "registered"
    shop_image_url: Optional[str] = None
    owner_image_url: Optional[str] = None
    total_earning: float = 0.0
    today_earnings: float = 0.0
    category_id: Optional[UUID] = None
    category: Optional[ShopCategoryResponse] = None
    product_categories: List[ProductCategoryResponse] = []

    class Config:
        from_attributes = True


# Response for the /nearby endpoint — includes how far the shop is
class ShopNearbyResponse(ShopResponse):
    distance_km: float  # Distance from the user in kilometers