from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# 1. The individual items in the cart
class OrderItemCreate(BaseModel):
    # Now Optional: If they upload a handwritten list, they might not send digital products!
    product_id: Optional[UUID] = None 
    quantity: int = 1
    # NEW: For requests like "270g only" or "Make the Biryani extra spicy"
    special_instructions: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    quantity: int
    price_at_time_of_order: float
    special_instructions: Optional[str] = None

    class Config:
        from_attributes = True

# 2. The main Checkout Payload
class OrderCreate(BaseModel):
    shop_id: UUID
    
    # NEW: Link to the handwritten list photo
    list_image_url: Optional[str] = None 
    
    # NEW: General instructions ("Deliver after 5 PM", "Call when downstairs")
    order_notes: Optional[str] = None
    
    # Pre-order & pickup fields
    order_type: str = "instant"                         # "instant" or "pre_order"
    scheduled_pickup_time: Optional[datetime] = None    # Required when order_type="pre_order"

    # Now Optional: Because a user can checkout with ONLY an image and 0 items!
    items: Optional[List[OrderItemCreate]] = [] 

class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    shop_id: UUID
    total_amount: float
    status: str
    list_image_url: Optional[str] = None
    order_notes: Optional[str] = None
    order_type: str
    scheduled_pickup_time: Optional[datetime] = None
    estimated_preparation_minutes: Optional[int] = None
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    # This is crucial for the chitty workflow! The shopkeeper calculates 
    # the loose items/photo list and enters the final real total here.
    total_amount: Optional[float] = None
    # Shopkeeper sets how long to prepare the order
    estimated_preparation_minutes: Optional[int] = None
