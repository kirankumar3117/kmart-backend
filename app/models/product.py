from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Info
    name = Column(String, index=True, nullable=False)  # e.g. "Aashirvaad Atta"
    category = Column(String, index=True)              # e.g. "Staples"
    description = Column(Text, nullable=True)
    
    # Media
    image_url = Column(String, nullable=True)
    
    # Pricing & Info
    mrp = Column(Float, nullable=False)                # Max Retail Price (Reference)
    unit = Column(String)                              # e.g. "1 kg", "500 ml"
    
    # Metadata
    barcode = Column(String, unique=True, index=True, nullable=True) # For scanning
    is_active = Column(Boolean, default=True)