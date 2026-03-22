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

class OrderItemProductDetail(BaseModel):
    id: UUID
    name: str
    image_url: Optional[str] = None
    unit: Optional[str] = None
    mrp: float

    class Config:
        from_attributes = True

class OrderItemResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    quantity: int
    price_at_time_of_order: float
    special_instructions: Optional[str] = None
    
    # NEW: Include full product details if a product_id exists
    product: Optional[OrderItemProductDetail] = None

    class Config:
        from_attributes = True

# 2. The main Checkout Payload
class OrderCreate(BaseModel):
    shop_id: UUID
    
    # NEW: Link to the handwritten list photos
    list_image_urls: Optional[List[str]] = []
    
    # NEW: General instructions ("Deliver after 5 PM", "Call when downstairs")
    order_notes: Optional[str] = None
    
    # Pre-order & pickup fields
    order_type: str = "instant"                         # "instant" or "pre_order"
    scheduled_pickup_time: Optional[datetime] = None    # Required when order_type="pre_order"

    # Now Optional: Because a user can checkout with ONLY an image and 0 items!
    items: Optional[List[OrderItemCreate]] = [] 

    model_config = {
        "json_schema_extra": {
            "example": {
                "shop_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "order_type": "instant",
                "scheduled_pickup_time": "2026-03-21T17:45:45.601Z",
                "list_image_urls": ["https://example.com/images/list.jpg", "https://example.com/images/list2.jpg"],
                "items": [
                    {
                        "product_id": "a57a3b1e-1963-4000-9c86-de1ba5372e97",
                        "quantity": 2,
                        "special_instructions": "Make it extra spicy"
                    }
                ]
            }
        }
    }

class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    shop_id: UUID
    total_amount: float
    status: str
    list_image_urls: Optional[List[str]] = []
    order_notes: Optional[str] = None
    order_type: str
    scheduled_pickup_time: Optional[datetime] = None
    estimated_preparation_minutes: Optional[int] = None
    created_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "0dd014db-932d-434c-aa65-e661f145d866",
                "customer_id": "554c58ce-0d6c-4c26-ba22-7c80f4d2d0e4",
                "shop_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "total_amount": 120.50,
                "status": "pending",
                "list_image_urls": ["https://example.com/images/list.jpg"],
                "order_notes": "Call me when you reach downstairs",
                "order_type": "instant",
                "scheduled_pickup_time": "2026-03-21T20:18:54.147Z",
                "estimated_preparation_minutes": 15,
                "created_at": "2026-03-21T20:18:54.147Z",
                "items": [
                    {
                        "id": "a2a8cf15-1129-4163-8e7c-269ed2bb0f0e",
                        "product_id": "a57a3b1e-1963-4000-9c86-de1ba5372e97",
                        "quantity": 2,
                        "price_at_time_of_order": 60.25,
                        "special_instructions": "Make it extra spicy"
                    }
                ]
            }
        }
    }



class OrderUpdate(BaseModel):
    status: Optional[str] = None
    # This is crucial for the chitty workflow! The shopkeeper calculates 
    # the loose items/photo list and enters the final real total here.
    total_amount: Optional[float] = None
    # Shopkeeper sets how long to prepare the order
    estimated_preparation_minutes: Optional[int] = None

class PaginatedOrderResponse(BaseModel):
    data: List[OrderResponse]
    total_count: int
    total_pages: int
    current_page: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [],
                "total_count": 45,
                "total_pages": 3,
                "current_page": 1
            }
        }
    }
