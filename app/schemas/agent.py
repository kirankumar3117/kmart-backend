from pydantic import BaseModel, Field
from typing import Optional

class AgentOnboardMerchantRequest(BaseModel):
    merchant_name: str
    phone_number: str
    pin: str = Field(..., min_length=4, max_length=4, description="The 4-digit PIN the merchant just typed")
    shop_name: str
    shop_location: str
    shop_image_url: Optional[str] = None
    merchant_image_url: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "merchant"
    agent_code: str = Field(..., min_length=4, max_length=4, description="The 4-digit Agent just typed")

