from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.models.cart_suggestion import CartSuggestion
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate
from app.schemas.cart_suggestion import CartSuggestionResponse
from app.utils.auth import get_current_user
from app.models.user import User
from app.core.ws_manager import manager  # <--- WebSocket Manager
from app.services.ocr import process_chitty_order  # <--- OCR Background Task


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
    # 1. Validate order_type
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
        list_image_url=order_data.list_image_url,
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
    if order_data.list_image_url:
        background_tasks.add_task(process_chitty_order, new_order.id)

    # 8. 🔔 Push real-time notification to the MERCHANT!
    await manager.send_to_user(shop.owner_id, {
        "type": "new_order",
        "order_id": new_order.id,
        "customer_name": current_user.full_name,
        "order_type": new_order.order_type,
        "scheduled_pickup_time": str(new_order.scheduled_pickup_time) if new_order.scheduled_pickup_time else None,
        "total_amount": new_order.total_amount,
        "item_count": len(order_items_to_create),
        "has_chitty": bool(order_data.list_image_url),
    })

    return new_order

# ==========================================
# GET ALL ORDERS FOR A SPECIFIC SHOP
# ==========================================
@router.get("/shop/{shop_id}", response_model=List[OrderResponse])
def get_shop_orders(
    shop_id: int,
    order_type: Optional[str] = Query(None, description="Filter by order type: instant or pre_order"),
    order_status: Optional[str] = Query(None, alias="status", description="Filter by status: pending, confirmed, etc."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # <--- Require Token
):
    # 1. Role-Based Check: Are they a merchant?
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Merchant access required."
        )

    # 2. Verify the shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    # 3. Build query with optional filters
    query = db.query(Order).filter(Order.shop_id == shop_id)

    if order_type:
        if order_type not in VALID_ORDER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid order_type filter. Must be one of: {VALID_ORDER_TYPES}")
        query = query.filter(Order.order_type == order_type)

    if order_status:
        if order_status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status filter. Must be one of: {VALID_STATUSES}")
        query = query.filter(Order.status == order_status)

    orders = query.order_by(Order.created_at.desc()).all()
    return orders

# ==========================================
# UPDATE ORDER STATUS & FINAL AMOUNT (Protected + WebSocket Push)
# ==========================================
@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int, 
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
        order.status = update_data.status
        
    if update_data.total_amount is not None:
        order.total_amount = update_data.total_amount

    if update_data.estimated_preparation_minutes is not None:
        order.estimated_preparation_minutes = update_data.estimated_preparation_minutes

    # 4. Save to database
    db.commit()
    db.refresh(order)
    
    # 5. 🔔 Push real-time update to the CUSTOMER via WebSocket!
    if update_data.status == "ready":
        # Special pickup-ready notification
        await manager.send_to_user(order.customer_id, {
            "type": "pickup_ready",
            "order_id": order.id,
            "shop_id": order.shop_id,
            "status": order.status,
            "estimated_preparation_minutes": order.estimated_preparation_minutes,
            "message": "Your order is ready for pickup!",
        })
    else:
        # Standard order update (confirmed, preparing, etc.)
        await manager.send_to_user(order.customer_id, {
            "type": "order_update",
            "order_id": order.id,
            "shop_id": order.shop_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "estimated_preparation_minutes": order.estimated_preparation_minutes,
            "updated_at": str(order.created_at),
        })
    
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
    order_id: int,
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