from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


# ==========================================
# NOTIFICATION SCHEMAS
# ==========================================
class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str
    type: str
    data: Optional[Any] = None
    is_read: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread_count: int
