from pydantic import BaseModel, Field
from typing import Optional

class MerchantRegisterRequest(BaseModel):
    merchant_name: str
    phone_number: str
    password: str = Field(..., min_length=4, description="Password for the merchant account")
    shop_name: str
    shop_location: str
    shop_image_url: Optional[str] = None
    merchant_image_url: Optional[str] = None
    email: Optional[str] = None
    shop_category_id: str = Field(..., description="The UUID of the shop category")
    stay_logged_in: bool = False

class MerchantLoginRequest(BaseModel):
    phone_number: str
    password: str
    stay_logged_in: bool = False
