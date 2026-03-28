import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ProductRequest(Base):
    __tablename__ = "product_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Who requested it
    merchant_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)

    # What was requested
    requested_name = Column(String, nullable=False)
    requested_image_url = Column(String, nullable=True)
    requested_price = Column(Float, nullable=False)
    requested_stock = Column(Integer, nullable=False, default=0)

    # Workflow status: pending | accepted | rejected
    status = Column(String, default="pending", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships for easy access
    merchant = relationship("User", foreign_keys=[merchant_user_id], lazy="joined")
    shop = relationship("Shop", foreign_keys=[shop_id], lazy="joined")
