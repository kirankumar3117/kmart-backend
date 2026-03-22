from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID

from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.models.cart_suggestion import CartSuggestion
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse
from app.schemas.cart_suggestion import CartSuggestionResponse
from app.utils.auth import get_current_user
from app.models.user import User
from app.services.notification_service import send_notification


router = APIRouter()

# ==========================================
# VALID ORDER TYPES & STATUSES
# ==========================================
VALID_ORDER_TYPES = {"instant", "pre_order"}
VALID_STATUSES = {"pending", "confirmed", "preparing", "ready", "picked_up", "delivered", "cancelled"}


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate, 
    background_tasks: BackgroundTasks,              # <--- For OCR processing
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # <--- THE SECURITY BOUNCER
):
    # 1. Role Check: Only customers can place orders
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403, 
            detail="Only customers can place orders."
        )

    # 2. Validate order_type
    if order_data.order_type not in VALID_ORDER_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid order_type '{order_data.order_type}'. Must be one of: {VALID_ORDER_TYPES}"
        )

    # 2. Pre-order validation: scheduled_pickup_time is REQUIRED and must be in the future
    if order_data.order_type == "pre_order":
        if order_data.scheduled_pickup_time is None:
            raise HTTPException(
                status_code=400,
                detail="scheduled_pickup_time is required for pre-orders."
            )
        if order_data.scheduled_pickup_time <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="scheduled_pickup_time must be in the future."
            )

    # 3. Verify the Shop exists
    shop = db.query(Shop).filter(Shop.id == order_data.shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    total_amount = 0.0
    order_items_to_create = []

    # 4. Process items ONLY IF the user actually selected digital items
    if order_data.items:
        for item in order_data.items:
            if item.product_id:
                inventory_item = db.query(InventoryItem).filter(
                    InventoryItem.shop_id == order_data.shop_id,
                    InventoryItem.product_id == item.product_id
                ).first()

                if not inventory_item:
                    raise HTTPException(status_code=400, detail=f"Product ID {item.product_id} is not sold here.")
                
                if inventory_item.stock < item.quantity:
                    raise HTTPException(status_code=400, detail=f"Not enough stock for Product ID {item.product_id}.")

                inventory_item.stock -= item.quantity
                item_price = inventory_item.price
                total_amount += (item_price * item.quantity)
            else:
                item_price = 0.0 

            order_items_to_create.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price_at_time_of_order": item_price,
                "special_instructions": item.special_instructions
            })

    # 5. Create the Main Order
    new_order = Order(
        customer_id=current_user.id,  # <--- SECURELY EXTRACTED FROM THE TOKEN!
        shop_id=order_data.shop_id,
        total_amount=total_amount,
        status="pending",
        order_type=order_data.order_type,
        scheduled_pickup_time=order_data.scheduled_pickup_time,
        list_image_urls=order_data.list_image_urls,
        order_notes=order_data.order_notes
    )
    db.add(new_order)
    db.flush() 

    # 6. Create the Order Items
    for oi_data in order_items_to_create:
        new_order_item = OrderItem(
            order_id=new_order.id, 
            product_id=oi_data["product_id"],
            quantity=oi_data["quantity"],
            price_at_time_of_order=oi_data["price_at_time_of_order"],
            special_instructions=oi_data["special_instructions"]
        )
        db.add(new_order_item)

    db.commit()
    db.refresh(new_order)

    # 7. 📸 If a chitty image was uploaded, trigger OCR in the background!
    if order_data.list_image_urls:
        from app.services.ocr import process_chitty_order
        background_tasks.add_task(process_chitty_order, new_order.id)

    # 8. 🔔 Push notification to the MERCHANT (persisted + WebSocket)
    await send_notification(
        user_id=str(shop.owner_id),
        title="🛒 New Order Received!",
        body=f"Order from {current_user.full_name} — {len(order_items_to_create)} item(s), ₹{new_order.total_amount:.2f}",
        notification_type="new_order",
        data={
            "order_id": str(new_order.id),
            "customer_name": current_user.full_name,
            "order_type": new_order.order_type,
            "scheduled_pickup_time": str(new_order.scheduled_pickup_time) if new_order.scheduled_pickup_time else None,
            "total_amount": new_order.total_amount,
            "item_count": len(order_items_to_create),
            "has_chitty": bool(order_data.list_image_urls),
        },
        db=db,
    )

    return new_order

# ==========================================
# GET ALL ORDERS FOR MERCHANTS'S SHOP
# ==========================================
@router.get("/merchant", response_model=PaginatedOrderResponse)
def get_merchant_orders(
    order_type: Optional[str] = Query(None, description="Filter by order type: instant or pre_order"),
    order_status: Optional[str] = Query(None, alias="status", description="Filter by status: pending, confirmed, etc."),
    skip: int = Query(0, description="Number of orders to skip (for pagination)"),
    limit: int = Query(20, description="Maximum number of orders to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # <--- Require Token
):
    # 1. Role-Based Check: Are they a merchant?
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Merchant access required."
        )

    # 2. Derive the shop from the merchant's user ID
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found for this merchant account.")
        
    # 3. Build query with optional filters
    query = db.query(Order).filter(Order.shop_id == shop.id)

    if order_type:
        if order_type not in VALID_ORDER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid order_type filter. Must be one of: {VALID_ORDER_TYPES}")
        query = query.filter(Order.order_type == order_type)

    if order_status:
        if order_status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status filter. Must be one of: {VALID_STATUSES}")
        query = query.filter(Order.status == order_status)

    import math
    total_count = query.count()
    total_pages = math.ceil(total_count / limit) if limit > 0 else 1
    current_page = (skip // limit) + 1 if limit > 0 else 1

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "data": orders,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": current_page
    }

# ==========================================
# UPDATE ORDER STATUS & FINAL AMOUNT (Protected + WebSocket Push)
# ==========================================
@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID, 
    update_data: OrderUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # <--- Require Token
):
    # 1. Role-Based Check
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Merchant access required."
        )

    # 2. Find the order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 3. Validate the new status if provided
    if update_data.status is not None:
        if update_data.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{update_data.status}'. Must be one of: {VALID_STATUSES}"
            )
        
        # --- Strict State Machine Enforcement ---
        current_status = order.status
        new_status = update_data.status
        
        # Define allowed next states map
        ALLOWED_TRANSITIONS = {
            "pending": ["confirmed", "cancelled"],
            "confirmed": ["preparing", "ready", "cancelled"],
            "preparing": ["ready"],
            "ready": ["picked_up", "delivered"],
            "picked_up": [], 
            "delivered": [],
            "cancelled": []
        }
        
        if new_status not in ALLOWED_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from '{current_status}' to '{new_status}'."
            )
            
        order.status = new_status
        
    if update_data.total_amount is not None:
        order.total_amount = update_data.total_amount

    if update_data.estimated_preparation_minutes is not None:
        order.estimated_preparation_minutes = update_data.estimated_preparation_minutes

    # 4. Save to database
    db.commit()
    db.refresh(order)
    
    # 5. 🔔 Push notification to the CUSTOMER (persisted + WebSocket)
    if update_data.status == "ready":
        await send_notification(
            user_id=str(order.customer_id),
            title="✅ Order Ready for Pickup!",
            body=f"Your order is ready! Head to the shop to pick it up.",
            notification_type="pickup_ready",
            data={
                "order_id": str(order.id),
                "shop_id": str(order.shop_id),
                "status": order.status,
                "estimated_preparation_minutes": order.estimated_preparation_minutes,
            },
            db=db,
        )
    elif update_data.status is not None:
        status_messages = {
            "confirmed": "Your order has been confirmed by the shop!",
            "preparing": "Your order is being prepared.",
            "picked_up": "Your order has been picked up.",
            "delivered": "Your order has been delivered. Enjoy!",
            "cancelled": "Your order has been cancelled.",
        }
        await send_notification(
            user_id=str(order.customer_id),
            title=f"📦 Order {update_data.status.replace('_', ' ').title()}",
            body=status_messages.get(update_data.status, f"Order status updated to: {update_data.status}"),
            notification_type="order_update",
            data={
                "order_id": str(order.id),
                "shop_id": str(order.shop_id),
                "status": order.status,
                "total_amount": order.total_amount,
                "estimated_preparation_minutes": order.estimated_preparation_minutes,
            },
            db=db,
        )
    
    return order


# ==========================================
# GET CUSTOMER'S OWN ORDERS (My Orders)
# ==========================================
@router.get("/me", response_model=List[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # <--- Require Token
):
    # Fetch all orders where the customer_id matches the logged-in user's token
    orders = db.query(Order).filter(Order.customer_id == current_user.id).order_by(Order.created_at.desc()).all()
    
    return orders


# ==========================================
# GET OCR SUGGESTIONS FOR AN ORDER (Merchant)
# ==========================================
@router.get("/{order_id}/suggestions", response_model=List[CartSuggestionResponse])
def get_order_suggestions(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify the order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Role check: only the merchant (or the customer themselves) can view suggestions
    if current_user.role == "merchant" or current_user.id == order.customer_id:
        suggestions = (
            db.query(CartSuggestion)
            .filter(CartSuggestion.order_id == order_id)
            .order_by(CartSuggestion.confidence.desc())
            .all()
        )
        return suggestions
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view suggestions for this order."
        )