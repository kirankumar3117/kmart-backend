from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class ShopBase(BaseModel):
    shop_name: str
    owner_name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ShopCreate(ShopBase):
    pass


class ShopResponse(ShopBase):
    id: UUID
    phone: str
    is_verified: bool = False
    is_onboarded: bool = False
    is_online: bool = False
    onboarding_step: str = "registered"
    shop_image_url: Optional[str] = None
    owner_image_url: Optional[str] = None

    class Config:
        from_attributes = True


# Response for the /nearby endpoint — includes how far the shop is
class ShopNearbyResponse(ShopResponse):
    distance_km: float  # Distance from the user in kilometers