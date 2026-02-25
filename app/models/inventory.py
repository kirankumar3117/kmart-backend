from sqlalchemy import Column, Integer, Float, ForeignKey
from app.db.base import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)

    # The Bridge Connections
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Store-specific details
    price = Column(Float, nullable=False)  # The price this specific shop is charging
    stock = Column(Integer, default=0)     # How many items they have on the shelf

        