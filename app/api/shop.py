from pydantic import BaseModel
from app.utils.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.shop import Shop
from app.models.user import User
from app.models.order import Order
from app.schemas.shop import ShopResponse
from app.services.notification_service import send_notification

router = APIRouter()


# 1. Create a quick schema for the request body
class ShopStatusUpdate(BaseModel):
    is_online: bool

# ==========================================
# GET  SHOP (Private)
# ==========================================
@router.get("/", response_model=ShopResponse)
def get_shop(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    print("shop" , shop)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop


# ==========================================
# UPDATE SHOP (Private)
# ==========================================
@router.put("/", response_model=ShopResponse)
async def update_shop(
    status_update: ShopStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    # 1. Role-Based Check: Are they a merchant?
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Merchant access required."
        )
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # 3. Update the shop with the value from the frontend
    old_status = shop.is_online
    shop.is_online = status_update.is_online
    
    # NEW logic: If going offline, reject all "pending" orders
    pending_orders = []
    if old_status and not status_update.is_online:
        pending_orders = db.query(Order).filter(
            Order.shop_id == shop.id,
            Order.status == "pending"
        ).all()
        
        for order in pending_orders:
            order.status = "rejected"
            
    db.commit()
    db.refresh(shop)

    # Trigger notifications for rejected orders after commit to ensure state is saved
    if pending_orders:
        for order in pending_orders:
            await send_notification(
                user_id=str(order.customer_id),
                title="📦 Order Rejected",
                body="The shop has gone offline. Your order has been rejected.",
                notification_type="order_update",
                data={
                    "order_id": str(order.id),
                    "status": "rejected",
                },
                db=db,
            )

    return shop