from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.session import get_db
from app.models.shop import Shop
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.user import User
from app.utils.auth import get_current_user
from app.schemas.shop import ShopResponse, ShopNearbyResponse, ShopUpdate
from app.schemas.inventory import ShopItemResponse

router = APIRouter()


# ==========================================
# GET SHOP ITEMS (Public: Joined Product + Inventory view)
# ==========================================
@router.get("/{shop_id}/items", response_model=List[ShopItemResponse])
def get_shop_items(
    shop_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    # 1. Verify the shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    # 2. Join InventoryItem with Product to get full product details + shop pricing
    results = (
        db.query(InventoryItem, Product)
        .join(Product, InventoryItem.product_id == Product.id)
        .filter(
            InventoryItem.shop_id == shop_id,
            InventoryItem.stock > 0,
            Product.is_active == True,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 3. Flatten the joined rows into a single response object
    shop_items = []
    for inv, prod in results:
        shop_items.append(
            ShopItemResponse(
                inventory_id=inv.id,
                product_id=prod.id,
                product_name=prod.name,
                category=prod.category,
                image_url=prod.image_url,
                mrp=prod.mrp,
                unit=prod.unit,
                price=inv.price,
                stock=inv.stock,
            )
        )

    return shop_items


# ==========================================
# GET NEARBY SHOPS (Public: Customers find shops near them!)
# ==========================================
@router.get("/nearby", response_model=List[ShopNearbyResponse])
def get_nearby_shops(
    user_lat: float = Query(..., description="User's latitude"),
    user_lng: float = Query(..., description="User's longitude"),
    radius_km: float = Query(10.0, description="Search radius in kilometers (default: 10km)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    R = 6371.0

    dlat = func.radians(Shop.latitude - user_lat)
    dlng = func.radians(Shop.longitude - user_lng)

    a = (
        func.power(func.sin(dlat / 2), 2)
        + func.cos(func.radians(user_lat))
        * func.cos(func.radians(Shop.latitude))
        * func.power(func.sin(dlng / 2), 2)
    )

    distance = R * 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))

    results = (
        db.query(Shop, distance.label("distance_km"))
        .filter(
            Shop.is_onboarded == True,
            Shop.latitude.isnot(None),
            Shop.longitude.isnot(None),
            distance <= radius_km,
        )
        .order_by(distance)
        .offset(skip)
        .limit(limit)
        .all()
    )

    nearby_shops = []
    for shop, dist in results:
        shop_data = ShopNearbyResponse.model_validate(shop)
        shop_data.distance_km = round(dist, 2)
        nearby_shops.append(shop_data)

    return nearby_shops


# ==========================================
# GET ALL SHOPS (Public: Customers need to see shops!)
# ==========================================
@router.get("/", response_model=List[ShopResponse])
@router.get("/", response_model=List[ShopResponse])
def get_shops(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    shops = db.query(Shop).offset(skip).limit(limit).all()
    return shops

# ==========================================
# UPDATE SHOP (Admin Only)
# ==========================================
@router.patch("/{shop_id}", response_model=ShopResponse)
def update_shop_as_admin(
    shop_id: str,
    body: ShopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Admin only
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    # 2. Find the shop
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    # 3. Apply updates
    update_data = body.model_dump(exclude_unset=True)
    
    # 3a. Update Product Categories directly on the shop
    if "product_category_ids" in update_data:
        pc_ids = update_data.pop("product_category_ids")
        if pc_ids is not None:
            product_cats = db.query(ProductCategory).filter(ProductCategory.id.in_(pc_ids)).all()
            if len(product_cats) != len(pc_ids):
                raise HTTPException(status_code=400, detail="One or more Product Category IDs are invalid.")
            shop.product_categories = product_cats
            
    # We ignore the offline/rejection logic here because Admins usually just fix metadata.
    # If admins also need to trigger offline rejection, we could add that logic here too.
    for key, value in update_data.items():
        setattr(shop, key, value)

    db.commit()
    db.refresh(shop)

    return shop