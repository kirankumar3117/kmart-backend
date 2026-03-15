from pydantic import BaseModel, Field
from typing import Optional

class AgentCreate(BaseModel):
    name: str = Field(..., description="Full Name of the Agent")
    agent_code: str = Field(..., description="Unique code for the Agent (e.g., AG01)")
    phone: str = Field(..., description="Phone number of the Agent")
    pin: str = Field(..., min_length=4, max_length=4, description="4-digit PIN for login")
    email: Optional[str] = None

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
    agent_code: Optional[str] = Field(None, min_length=4, max_length=4, description="The 4-digit Agent just typed")
    shop_category_id: str = Field(..., description="The UUID of the shop category")

class AgentStatusUpdate(BaseModel):
    is_active: bool

