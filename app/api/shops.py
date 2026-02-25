from app.utils.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.session import get_db
from app.models.shop import Shop
from app.models.user import User
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.schemas.shop import ShopCreate, ShopResponse, ShopNearbyResponse
from app.schemas.inventory import ShopItemResponse

router = APIRouter()

# ==========================================
# GET SHOP ITEMS (Public: Joined Product + Inventory view)
# ==========================================
@router.get("/{shop_id}/items", response_model=List[ShopItemResponse])
def get_shop_items(
    shop_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
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
            InventoryItem.stock > 0,        # Only in-stock items
            Product.is_active == True        # Only active products
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 3. Flatten the joined rows into a single response object
    shop_items = []
    for inv, prod in results:
        shop_items.append(ShopItemResponse(
            inventory_id=inv.id,
            product_id=prod.id,
            product_name=prod.name,
            category=prod.category,
            image_url=prod.image_url,
            mrp=prod.mrp,
            unit=prod.unit,
            price=inv.price,
            stock=inv.stock,
        ))

    return shop_items

# ==========================================
# CREATE A SHOP (Protected: Shopkeepers Only)
# ==========================================
@router.post("/", response_model=ShopResponse)
def create_shop(
    shop: ShopCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Security Token
):
    # 1. Verify they are actually a shopkeeper
    if current_user.role != "shopkeeper":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only shopkeepers can register a new shop."
        )

    # 2. Mash the frontend data and the secure token ID together
    # **shop.model_dump() unpacks the JSON body (name, category, etc.)
    db_shop = Shop(**shop.model_dump(), owner_id=current_user.id)
    
    # 3. Save to Postgres
    db.add(db_shop)
    db.commit()
    db.refresh(db_shop)
    
    return db_shop

# ==========================================
# GET NEARBY SHOPS (Public: Customers find shops near them!)
# ==========================================
# Uses the Haversine Formula to calculate distance in kilometers
# Formula: d = 2R × arcsin(√(sin²((Δlat)/2) + cos(lat1)·cos(lat2)·sin²((Δlng)/2)))
# ==========================================
@router.get("/nearby", response_model=List[ShopNearbyResponse])
def get_nearby_shops(
    user_lat: float = Query(..., description="User's latitude"),
    user_lng: float = Query(..., description="User's longitude"),
    radius_km: float = Query(10.0, description="Search radius in kilometers (default: 10km)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Earth's radius in kilometers
    R = 6371.0

    # Build the Haversine distance expression using PostgreSQL math functions
    dlat = func.radians(Shop.latitude - user_lat)
    dlng = func.radians(Shop.longitude - user_lng)
    
    a = (
        func.power(func.sin(dlat / 2), 2) +
        func.cos(func.radians(user_lat)) *
        func.cos(func.radians(Shop.latitude)) *
        func.power(func.sin(dlng / 2), 2)
    )
    
    distance = R * 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))

    # Query: select shops + computed distance, filter within radius, sort by nearest
    results = (
        db.query(Shop, distance.label("distance_km"))
        .filter(
            Shop.is_active == True,
            Shop.latitude.isnot(None),     # Skip shops without coordinates
            Shop.longitude.isnot(None),
            distance <= radius_km           # Only within the radius
        )
        .order_by(distance)                 # Nearest first
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Merge the Shop fields + distance_km into a single response
    nearby_shops = []
    for shop, dist in results:
        shop_data = ShopNearbyResponse.model_validate(shop)
        shop_data.distance_km = round(dist, 2)  # Round to 2 decimal places
        nearby_shops.append(shop_data)

    return nearby_shops

# ==========================================
# GET ALL SHOPS (Public: Customers need to see shops!)
# ==========================================
@router.get("/", response_model=List[ShopResponse])
def get_shops(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    shops = db.query(Shop).offset(skip).limit(limit).all()
    return shops