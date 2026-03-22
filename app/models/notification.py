import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Who receives this notification
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Notification content
    title = Column(String, nullable=False)           # e.g. "New Order Received!"
    body = Column(Text, nullable=False)              # e.g. "Order #abc from Kiran Kumar - 3 items"
    type = Column(String, nullable=False, index=True) # new_order, order_update, pickup_ready

    # Additional data (order_id, shop_id, etc.) — flexible JSON
    data = Column(JSON, nullable=True)

    # Read status
    is_read = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
