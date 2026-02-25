from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate
from app.utils.auth import get_current_user
from app.models.user import User


router = APIRouter()

@router.post("/", response_model=OrderResponse)
def create_order(
    order_data: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- THE SECURITY BOUNCER
):
    # 1. Verify the Shop exists
    shop = db.query(Shop).filter(Shop.id == order_data.shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    total_amount = 0.0
    order_items_to_create = []

    # 2. Process items ONLY IF the user actually selected digital items
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

    # 3. Create the Main Order
    new_order = Order(
        customer_id=current_user.id, # <--- SECURELY EXTRACTED FROM THE TOKEN!
        shop_id=order_data.shop_id,
        total_amount=total_amount,
        status="pending",
        list_image_url=order_data.list_image_url,
        order_notes=order_data.order_notes
    )
    db.add(new_order)
    db.flush() 

    # 4. Create the Order Items
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

    return new_order

# ==========================================
# GET ALL ORDERS FOR A SPECIFIC SHOP
# ==========================================
@router.get("/shop/{shop_id}", response_model=List[OrderResponse])
def get_shop_orders(
    shop_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Require Token
):
    # 1. Role-Based Check: Are they a shopkeeper?
    if current_user.role != "shopkeeper":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Shopkeeper access required."
        )

    # 2. Verify the shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    # 3. Fetch orders
    orders = db.query(Order).filter(Order.shop_id == shop_id).order_by(Order.created_at.desc()).all()
    return orders

# ==========================================
# UPDATE ORDER STATUS & FINAL AMOUNT (Protected)
# ==========================================
@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int, 
    update_data: OrderUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Require Token
):
    # 1. Role-Based Check
    if current_user.role != "shopkeeper":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized. Shopkeeper access required."
        )

    # 2. Find the order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 3. Update the data
    if update_data.status is not None:
        order.status = update_data.status
        
    if update_data.total_amount is not None:
        order.total_amount = update_data.total_amount

    # 4. Save to database
    db.commit()
    db.refresh(order)
    
    return order


# ==========================================
# GET CUSTOMER'S OWN ORDERS (My Orders)
# ==========================================
@router.get("/me", response_model=List[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Require Token
):
    # Fetch all orders where the customer_id matches the logged-in user's token
    orders = db.query(Order).filter(Order.customer_id == current_user.id).order_by(Order.created_at.desc()).all()
    
    return orders