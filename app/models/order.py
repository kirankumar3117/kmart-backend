from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    
    total_amount = Column(Float, default=0.0)
    status = Column(String, default="pending")

    # Pre-order & pickup fields
    order_type = Column(String, default="instant")  # "instant" | "pre_order"
    scheduled_pickup_time = Column(DateTime(timezone=True), nullable=True)
    estimated_preparation_minutes = Column(Integer, nullable=True)
    
    # NEW: Store the URL of the uploaded handwritten list or image
    list_image_url = Column(String, nullable=True) 
    
    # NEW: General instructions for the whole order (e.g., "Deliver after 5 PM")
    order_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("OrderItem", backref="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # We make this True (optional) because if they upload a photo list, 
    # they might not select specific digital products at checkout!
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    quantity = Column(Integer, nullable=False, default=1)
    price_at_time_of_order = Column(Float, nullable=False, default=0.0)
    
    # NEW: For requests like "Need exactly 270 grams" or "Make the Biryani spicy"
    special_instructions = Column(String, nullable=True)