import uuid
from sqlalchemy import Column, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


# ==========================================
# ASSOCIATION TABLE: ShopCategory <-> ProductCategory (Many-to-Many)
# ==========================================
shop_category_product_category_link = Table(
    "shop_category_product_category_link",
    Base.metadata,
    Column("shop_category_id", UUID(as_uuid=True), ForeignKey("shop_categories.id", ondelete="CASCADE"), primary_key=True),
    Column("product_category_id", UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="CASCADE"), primary_key=True),
)


class ShopCategory(Base):
    __tablename__ = "shop_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Many-to-many: which product categories belong to this shop type
    product_categories = relationship(
        "ProductCategory",
        secondary=shop_category_product_category_link,
        backref="shop_categories",
        lazy="joined",
    )
