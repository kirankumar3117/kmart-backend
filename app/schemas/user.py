from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

class UserCreate(BaseModel):
    email: Optional[EmailStr] = None # Now optional!
    password: str
    full_name: str
    phone_number: str
    # 'customer', 'shopkeeper', or 'admin'. Defaults to 'customer'.
    role: Optional[str] = "customer" 

    @field_validator('email', mode='before')
    @classmethod
    def treat_empty_email_as_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None  # <--- THIS IS THE CRITICAL FIX
    role: str
    is_active: bool
    is_verified: bool
    onboarding_step: str

    class Config:
        from_attributes = True

# Add this new schema
class UserLogin(BaseModel):
    phone_number: str
    password: str
    role: str