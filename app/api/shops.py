from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.session import get_db
from app.models.shop import Shop
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.schemas.shop import ShopResponse, ShopNearbyResponse
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
def get_shops(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    shops = db.query(Shop).offset(skip).limit(limit).all()
    return shops