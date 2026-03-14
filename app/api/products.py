from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.product import Product
from app.models.product_category import ProductCategory, product_category_link
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.utils.auth import get_current_user

router = APIRouter()


# ==========================================
# HELPER: Check ownership or admin
# ==========================================
def _check_product_access(product: Product, current_user: User):
    """Merchants can only modify their own products. Admins can modify any."""
    if current_user.role == "admin":
        return  # Admin bypasses all ownership checks

    if current_user.role != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only merchants and admins can manage products.",
        )

    if product.merchant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own products.",
        )


# ==========================================
# HELPER: Resolve category IDs to ProductCategory objects
# ==========================================
def _resolve_categories(category_ids: List[int], db: Session) -> List[ProductCategory]:
    categories = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.id.in_(category_ids),
            ProductCategory.is_deleted == False,
            ProductCategory.is_active == True,
        )
        .all()
    )
    if len(categories) != len(category_ids):
        found_ids = {c.id for c in categories}
        missing = [cid for cid in category_ids if cid not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or inactive category IDs: {missing}",
        )
    return categories


# ==========================================
# 1. CREATE PRODUCT (Merchant / Admin)
# ==========================================
@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only merchants and admins can create products
    if current_user.role not in ("merchant", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only merchants and admins can create products.",
        )

    # Check for duplicate barcode if provided
    if body.barcode:
        existing = db.query(Product).filter(Product.barcode == body.barcode).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this barcode already exists.",
            )

    # Resolve categories
    categories = _resolve_categories(body.category_ids, db)

    # Create product
    product_data = body.model_dump(exclude={"category_ids"})
    new_product = Product(**product_data, merchant_id=current_user.id)
    new_product.categories = categories

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


# ==========================================
# 2. LIST / SEARCH PRODUCTS (Public)
# Filters: category_id, search (name), merchant_id
# Always returns only active + non-deleted products
# ==========================================
@router.get("/", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = Query(None, description="Search by product name"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    merchant_id: Optional[int] = Query(None, description="Filter by merchant ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(
        Product.is_active == True,
        Product.is_deleted == False,
    )

    # Filter by product name (case-insensitive)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Filter by category (via many-to-many join)
    if category_id:
        query = query.join(product_category_link).filter(
            product_category_link.c.category_id == category_id
        )

    # Filter by merchant
    if merchant_id:
        query = query.filter(Product.merchant_id == merchant_id)

    return query.offset(skip).limit(limit).all()


# ==========================================
# 3. GET SINGLE PRODUCT (Public)
# ==========================================
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


# ==========================================
# 4. UPDATE PRODUCT (Merchant: own only / Admin: any)
# ==========================================
@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    # Access control
    _check_product_access(product, current_user)

    update_data = body.model_dump(exclude_unset=True)

    # Handle category update separately
    if "category_ids" in update_data:
        category_ids = update_data.pop("category_ids")
        product.categories = _resolve_categories(category_ids, db)

    # Check barcode uniqueness if changing
    if "barcode" in update_data and update_data["barcode"]:
        existing = (
            db.query(Product)
            .filter(Product.barcode == update_data["barcode"], Product.id != product_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another product with this barcode already exists.",
            )

    # Apply remaining updates
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


# ==========================================
# 5. DEACTIVATE PRODUCT (Merchant: own only / Admin: any)
# ==========================================
@router.patch("/{product_id}/deactivate", response_model=ProductResponse)
def deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    _check_product_access(product, current_user)

    product.is_active = False
    db.commit()
    db.refresh(product)
    return product


# ==========================================
# 6. SOFT DELETE PRODUCT (Merchant: own only / Admin: any)
# ==========================================
@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    _check_product_access(product, current_user)

    product.is_deleted = True
    product.is_active = False
    db.commit()

    return {
        "success": True,
        "message": f"Product '{product.name}' has been soft deleted.",
    }