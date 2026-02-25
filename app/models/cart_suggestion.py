from sqlalchemy import Column, Integer, Float, String, ForeignKey
from app.db.base import Base

class CartSuggestion(Base):
    __tablename__ = "cart_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Which order this suggestion belongs to
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    
    # The raw text line extracted by OCR (e.g. "Aashirvaad Atta 10kg")
    extracted_text = Column(String, nullable=False)
    
    # The matched product from our database (nullable if no match found)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String, nullable=True)  # Denormalized for quick display
    
    # How confident we are in the match (0.0 to 1.0)
    confidence = Column(Float, default=0.0)
    
    # Shopkeeper can accept or reject each suggestion
    # Values: "suggested", "accepted", "rejected"
    status = Column(String, default="suggested")
