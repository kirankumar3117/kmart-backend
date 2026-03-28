from pydantic import BaseModel
from app.utils.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import func

from app.db.session import get_db
from app.models.shop import Shop
from app.models.product_category import ProductCategory
from app.models.user import User
from app.models.order import Order
from app.schemas.shop import ShopResponse, ShopUpdate
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
        
    # Calculate Earnings
    total_earning = db.query(func.sum(Order.total_amount)).filter(
        Order.shop_id == shop.id,
        Order.status.notin_(["cancelled", "rejected"])
    ).scalar() or 0.0

    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_earnings = db.query(func.sum(Order.total_amount)).filter(
        Order.shop_id == shop.id,
        Order.status.notin_(["cancelled", "rejected"]),
        Order.created_at >= start_of_today
    ).scalar() or 0.0

    setattr(shop, 'total_earning', total_earning)
    setattr(shop, 'today_earnings', today_earnings)

    return shop


# ==========================================
# UPDATE SHOP (Private - Partial)
# ==========================================
@router.patch("/", response_model=ShopResponse)
async def update_shop(
    body: ShopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Role-Based Check: Are they a merchant?
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Merchant access required."
        )
    
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    update_data = body.model_dump(exclude_unset=True)
    
    # Handle status change logic (offline rejections)
    pending_orders = []
    if "is_online" in update_data:
        old_status = shop.is_online
        new_status = update_data["is_online"]
        
        if old_status and not new_status:
            # Going offline: reject pending orders
            pending_orders = db.query(Order).filter(
                Order.shop_id == shop.id,
                Order.status == "pending"
            ).all()
            
            for order in pending_orders:
                order.status = "rejected"
    
    
    # Apply special update: Product Categories
    if "product_category_ids" in update_data:
        pc_ids = update_data.pop("product_category_ids")
        if pc_ids is not None:
            product_cats = db.query(ProductCategory).filter(ProductCategory.id.in_(pc_ids)).all()
            if len(product_cats) != len(pc_ids):
                raise HTTPException(status_code=400, detail="One or more Product Category IDs are invalid.")
            shop.product_categories = product_cats
            
    # Apply standard updates
    if "category_id" in update_data and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only admins can change the shop category (shop type)."
        )
        
    for key, value in update_data.items():
        setattr(shop, key, value)

    db.commit()
    db.refresh(shop)

    # Trigger notifications for rejected orders
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