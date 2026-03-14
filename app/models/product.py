from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.models.product_category import product_category_link


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # Ownership: which merchant created this product
    merchant_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Core Info
    name = Column(String, index=True, nullable=False)       # e.g. "Aashirvaad Atta"
    description = Column(Text, nullable=True)

    # Media
    image_url = Column(String, nullable=True)

    # Pricing & Info
    mrp = Column(Float, nullable=False)                     # Max Retail Price (Reference)
    unit = Column(String)                                   # e.g. "1 kg", "500 ml"

    # Metadata
    barcode = Column(String, unique=True, index=True, nullable=True)  # For scanning

    # Status flags
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Many-to-Many relationship with ProductCategory
    categories = relationship(
        "ProductCategory",
        secondary=product_category_link,
        backref="products",
        lazy="joined",
    )