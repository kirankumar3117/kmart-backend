from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class CartSuggestionResponse(BaseModel):
    id: UUID
    order_id: UUID
    extracted_text: str              # Raw OCR text (e.g. "Aashirvaad Atta 10kg")
    product_id: Optional[UUID] = None # Matched product ID (None if no match)
    product_name: Optional[str] = None
    confidence: float                # 0.0 to 1.0
    status: str                      # "suggested", "accepted", "rejected"

    class Config:
        from_attributes = True
