from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter()

@router.post("/", response_model=OrderResponse)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    # 1. Verify the Shop exists
    shop = db.query(Shop).filter(Shop.id == order_data.shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    total_amount = 0.0
    order_items_to_create = []

    # 2. Process items ONLY IF the user actually selected digital items
    if order_data.items:
        for item in order_data.items:
            # If they provided a product_id, check the stock
            if item.product_id:
                inventory_item = db.query(InventoryItem).filter(
                    InventoryItem.shop_id == order_data.shop_id,
                    InventoryItem.product_id == item.product_id
                ).first()

                if not inventory_item:
                    raise HTTPException(status_code=400, detail=f"Product ID {item.product_id} is not sold here.")
                
                # Check stock limits (unless it's a custom loose request, but we'll keep it strict for now)
                if inventory_item.stock < item.quantity:
                    raise HTTPException(status_code=400, detail=f"Not enough stock for Product ID {item.product_id}.")

                inventory_item.stock -= item.quantity
                item_price = inventory_item.price
                total_amount += (item_price * item.quantity)
            else:
                # If they didn't provide a product_id, it's a purely custom line item
                item_price = 0.0 # Shopkeeper will update this later!

            # Save the parsed item data
            order_items_to_create.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price_at_time_of_order": item_price,
                "special_instructions": item.special_instructions
            })

    # 3. Create the Main Order (works for both normal orders AND photo orders)
    new_order = Order(
        customer_id=order_data.customer_id,
        shop_id=order_data.shop_id,
        total_amount=total_amount,
        status="pending",
        list_image_url=order_data.list_image_url,
        order_notes=order_data.order_notes
    )
    db.add(new_order)
    db.flush() 

    # 4. Create the Order Items (if there are any)
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