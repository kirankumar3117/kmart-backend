from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID as PyUUID

from app.db.session import get_db
from app.models.product import Product
from app.models.product_category import ProductCategory, product_category_link
from app.models.product_subcategory import ProductSubcategory
from app.models.inventory import InventoryItem
from app.models.shop import Shop
from app.models.shop_category import ShopCategory
from app.models.product_request import ProductRequest
from app.models.user import User
from app.schemas.product import ProductResponse
from app.schemas.product_request import (
    ProductRequestCreate,
    ProductRequestResponse,
    AdminReviewPayload,
)
from app.utils.auth import get_current_user

router = APIRouter()


# ==========================================
# FLOW 1: MERCHANT DISCOVERY
# Show products the merchant could add but hasn't yet
# ==========================================
@router.get("/discover", response_model=List[ProductResponse])
def discover_products(
    category_id: Optional[PyUUID] = Query(None, description="Override: filter by a specific product category ID"),
    search: Optional[str] = Query(None, description="Search by product name"),
    skip: int = Query(0),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Only merchants
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant access required.",
        )

    # 2. Get merchant's shop
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found for this merchant.")

    # 3. Determine allowed product categories
    allowed_category_ids = []
    
    # PRIORITY 1: Product categories assigned directly to THIS shop
    if shop.product_categories:
        allowed_category_ids = [pc.id for pc in shop.product_categories]
    # PRIORITY 2: Fallback to the default categories for the shop's Type
    elif shop.category_id:
        shop_cat = db.query(ShopCategory).filter(ShopCategory.id == shop.category_id).first()
        if shop_cat and shop_cat.product_categories:
            allowed_category_ids = [pc.id for pc in shop_cat.product_categories]

    if not allowed_category_ids:
        # If the shop has no product categories assigned, return empty list immediately
        return []

    target_category_ids = allowed_category_ids

    if category_id:
        # Frontend override — use the explicit category ONLY IF it is allowed for this shop
        if category_id not in allowed_category_ids:
            return []
        target_category_ids = [category_id]
    else:
        # Filter by product categories via many-to-many join
        query = (
            db.query(Product)
            .join(product_category_link)
            .filter(
                product_category_link.c.category_id.in_(target_category_ids),
                Product.is_active == True,
                Product.is_deleted == False,
            )
        )

    # 4. EXCLUSION: Remove products already in this merchant's inventory
    existing_product_ids = (
        db.query(InventoryItem.product_id)
        .filter(InventoryItem.shop_id == shop.id)
        .subquery()
    )
    query = query.filter(~Product.id.in_(existing_product_ids))

    # 5. Optional search
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    return query.distinct().offset(skip).limit(limit).all()


# ==========================================
# FLOW 2: MERCHANT SUBMITS PRODUCT REQUEST
# ==========================================
@router.post("/", response_model=ProductRequestResponse, status_code=201)
def create_product_request(
    body: ProductRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Only merchants
    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only merchants can submit product requests.",
        )

    # 2. Get merchant's shop
    shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found for this merchant.")

    # 3. Create the request
    new_request = ProductRequest(
        merchant_user_id=current_user.id,
        shop_id=shop.id,
        requested_name=body.requested_name,
        requested_image_url=body.requested_image_url,
        requested_price=body.requested_price,
        requested_stock=body.requested_stock,
        status="pending",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return new_request


# ==========================================
# LIST PRODUCT REQUESTS
# Admin sees all, Merchant sees own
# ==========================================
@router.get("/", response_model=List[ProductRequestResponse])
def list_product_requests(
    request_status: Optional[str] = Query(None, alias="status", description="Filter: pending, accepted, rejected"),
    skip: int = Query(0),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ProductRequest)

    if current_user.role == "admin":
        pass  # Admin sees everything
    elif current_user.role == "merchant":
        query = query.filter(ProductRequest.merchant_user_id == current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized.",
        )

    if request_status:
        if request_status not in ("pending", "accepted", "rejected"):
            raise HTTPException(status_code=400, detail="Invalid status filter.")
        query = query.filter(ProductRequest.status == request_status)

    return query.order_by(ProductRequest.created_at.desc()).offset(skip).limit(limit).all()


# ==========================================
# FLOW 3: ADMIN REVIEW & ONBOARDING
# ==========================================
@router.patch("/{request_id}/review", response_model=ProductRequestResponse)
def review_product_request(
    request_id: PyUUID,
    body: AdminReviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Admin only
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can review product requests.",
        )

    # 2. Find the request
    product_request = db.query(ProductRequest).filter(ProductRequest.id == request_id).first()
    if not product_request:
        raise HTTPException(status_code=404, detail="Product request not found.")

    if product_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request already {product_request.status}. Cannot review again.",
        )

    # 3. Validate action
    if body.action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'.")

    # ---- REJECT ----
    if body.action == "reject":
        product_request.status = "rejected"
        db.commit()
        db.refresh(product_request)
        return product_request

    # ---- ACCEPT (single transaction) ----
    if not body.product_payload:
        raise HTTPException(
            status_code=400,
            detail="product_payload is required when accepting a request.",
        )

    payload = body.product_payload

    # 3a. Validate categories exist
    categories = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.id.in_(payload.category_ids),
            ProductCategory.is_deleted == False,
            ProductCategory.is_active == True,
        )
        .all()
    )
    if len(categories) != len(payload.category_ids):
        found_ids = {c.id for c in categories}
        missing = [str(cid) for cid in payload.category_ids if cid not in found_ids]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or inactive category IDs: {missing}",
        )

    # 3b. Validate subcategory if provided
    if payload.subcategory_id:
        subcategory = (
            db.query(ProductSubcategory)
            .filter(
                ProductSubcategory.id == payload.subcategory_id,
                ProductSubcategory.is_deleted == False,
                ProductSubcategory.is_active == True,
            )
            .first()
        )
        if not subcategory:
            raise HTTPException(status_code=400, detail="Subcategory not found or inactive.")
        if subcategory.category_id not in payload.category_ids:
            raise HTTPException(
                status_code=400,
                detail="Subcategory does not belong to any of the selected categories.",
            )

    # 3c. Check barcode uniqueness
    if payload.barcode:
        existing = db.query(Product).filter(Product.barcode == payload.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Product with this barcode already exists.")

    # STEP 1: Create the new global Product
    product_data = payload.model_dump(exclude={"category_ids"})
    new_product = Product(
        **product_data,
        created_by_id=current_user.id,  # Admin is creating this on behalf
    )
    new_product.categories = categories
    db.add(new_product)
    db.flush()  # Get the new product_id without committing

    # STEP 2: Create Inventory record for the merchant's shop
    new_inventory = InventoryItem(
        shop_id=product_request.shop_id,
        product_id=new_product.id,
        price=product_request.requested_price,
        stock=product_request.requested_stock,
        in_stock=product_request.requested_stock > 0,
    )
    db.add(new_inventory)

    # STEP 3: Update request status
    product_request.status = "accepted"

    # STEP 4: Commit everything in one transaction
    db.commit()
    db.refresh(product_request)

    return product_request
