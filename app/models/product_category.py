from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Table, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

# ==========================================
# ASSOCIATION TABLE: Product <-> ProductCategory (Many-to-Many)
# ==========================================
product_category_link = Table(
    "product_category_link",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("product_categories.id", ondelete="CASCADE"), primary_key=True),
)


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)

    # Status flags
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
