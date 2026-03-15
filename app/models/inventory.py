import uuid
from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # The Bridge Connections
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Store-specific details
    price = Column(Float, nullable=False)  # The price this specific shop is charging
    stock = Column(Integer, default=0)     # How many items they have on the shelf