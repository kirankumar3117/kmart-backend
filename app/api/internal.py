from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.models.order import Order
from app.models.shop import Shop
from app.models.user import User
from app.core.config import settings
from app.services.notification_service import send_notification

router = APIRouter()

@router.post("/cron/check-timeouts")
async def check_order_timeouts(
    x_cron_secret: str = Header(..., description="Secret key to authorize cron execution"),
    db: Session = Depends(get_db)
):
    """
    Called by an external cron service (e.g. cron-job.org) every X minutes.
    Finds orders pending for > 15 minutes, logs them, and sends an FCM push to the admin.
    """
    # 1. Authorize
    if x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized cron request"
        )
        
    # 2. Find pending orders older than 15 minutes
    timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
    
    overdue_orders = db.query(Order).filter(
        Order.status == "pending",
        Order.created_at < timeout_threshold
    ).all()
    
    if not overdue_orders:
        return {"success": True, "message": "No overdue orders found", "count": 0}
        
    # 3. Find admins to notify
    admins = db.query(User).filter(User.role == "admin").all()
    
    # 4. Process each overdue order
    processed_count = 0
    for order in overdue_orders:
        shop = db.query(Shop).filter(Shop.id == order.shop_id).first()
        shop_name = shop.shop_name if shop else "Unknown Shop"
        
        # We don't change the status (merchant could still technically accept it late),
        # we just alert the admin so they can call the shop contextually.
        
        for admin in admins:
            await send_notification(
                user_id=str(admin.id),
                title="🚨 Overdue Order Alert!",
                body=f"Order {order.id} at {shop_name} has been pending for over 15 minutes!",
                notification_type="order_timeout",
                data={
                    "order_id": str(order.id),
                    "shop_id": str(order.shop_id),
                    "shop_name": shop_name,
                    "created_at": str(order.created_at)
                },
                db=db
            )
        processed_count += 1
        
    return {
        "success": True, 
        "message": f"Processed {processed_count} overdue orders",
        "count": processed_count
    }
