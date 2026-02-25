from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: Optional[EmailStr] = None # Now optional!
    password: str
    full_name: str
    phone_number: str
    # 'customer', 'shopkeeper', or 'admin'. Defaults to 'customer'.
    role: Optional[str] = "customer" 

class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None  # <--- THIS IS THE CRITICAL FIX
    role: str
    is_active: bool

    class Config:
        from_attributes = True

# Add this new schema
class UserLogin(BaseModel):
    phone_number: str
    password: str
    role: str