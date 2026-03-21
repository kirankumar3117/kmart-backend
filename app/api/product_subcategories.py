from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models.product_subcategory import ProductSubcategory
from app.models.product_category import ProductCategory
from app.models.user import User
from app.schemas.product_subcategory import (
    ProductSubcategoryCreate,
    ProductSubcategoryUpdate,
    ProductSubcategoryResponse,
)
from app.utils.auth import get_current_user

router = APIRouter()


# ==========================================
# HELPER: Admin-only check
# ==========================================
def _require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage product subcategories.",
        )


# ==========================================
# HELPER: Build response with category_name
# ==========================================
def _build_response(subcategory: ProductSubcategory) -> dict:
    data = {
        "id": subcategory.id,
        "category_id": subcategory.category_id,
        "category_name": subcategory.category.name if subcategory.category else None,
        "name": subcategory.name,
        "description": subcategory.description,
        "image_url": subcategory.image_url,
        "is_active": subcategory.is_active,
        "is_deleted": subcategory.is_deleted,
        "created_at": subcategory.created_at,
        "updated_at": subcategory.updated_at,
    }
    return data


# ==========================================
# 1. CREATE PRODUCT SUBCATEGORY (Admin Only)
# ==========================================
@router.post("/", response_model=ProductSubcategoryResponse, status_code=201)
def create_product_subcategory(
    body: ProductSubcategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    # Validate parent category exists and is active
    category = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.id == body.category_id,
            ProductCategory.is_deleted == False,
            ProductCategory.is_active == True,
        )
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent category not found or is inactive.",
        )

    # Check duplicate name within the same category
    existing = (
        db.query(ProductSubcategory)
        .filter(
            ProductSubcategory.name == body.name,
            ProductSubcategory.category_id == body.category_id,
            ProductSubcategory.is_deleted == False,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A subcategory '{body.name}' already exists under this category.",
        )

    new_subcategory = ProductSubcategory(**body.model_dump())
    db.add(new_subcategory)
    db.commit()
    db.refresh(new_subcategory)

    return _build_response(new_subcategory)


# ==========================================
# 2. LIST PRODUCT SUBCATEGORIES (Public)
# Filter by category_id (optional)
# ==========================================
@router.get("/", response_model=List[ProductSubcategoryResponse])
def list_product_subcategories(
    category_id: Optional[str] = Query(None, description="Filter by parent category ID"),
    db: Session = Depends(get_db),
):
    query = db.query(ProductSubcategory).filter(
        ProductSubcategory.is_active == True,
        ProductSubcategory.is_deleted == False,
    )

    if category_id:
        query = query.filter(ProductSubcategory.category_id == category_id)

    subcategories = query.order_by(ProductSubcategory.name.asc()).all()
    return [_build_response(s) for s in subcategories]


# ==========================================
# 3. GET SINGLE PRODUCT SUBCATEGORY (Public)
# ==========================================
@router.get("/{subcategory_id}", response_model=ProductSubcategoryResponse)
def get_product_subcategory(
    subcategory_id: UUID,
    db: Session = Depends(get_db),
):
    subcategory = (
        db.query(ProductSubcategory)
        .filter(ProductSubcategory.id == subcategory_id)
        .first()
    )
    if not subcategory or subcategory.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subcategory not found.",
        )

    return _build_response(subcategory)


# ==========================================
# 4. UPDATE PRODUCT SUBCATEGORY (Admin Only)
# ==========================================
@router.patch("/{subcategory_id}", response_model=ProductSubcategoryResponse)
def update_product_subcategory(
    subcategory_id: UUID,
    body: ProductSubcategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    subcategory = (
        db.query(ProductSubcategory)
        .filter(ProductSubcategory.id == subcategory_id)
        .first()
    )
    if not subcategory or subcategory.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subcategory not found.",
        )

    update_data = body.model_dump(exclude_unset=True)

    # Check duplicate name within same category if name is changing
    if "name" in update_data:
        existing = (
            db.query(ProductSubcategory)
            .filter(
                ProductSubcategory.name == update_data["name"],
                ProductSubcategory.category_id == subcategory.category_id,
                ProductSubcategory.id != subcategory_id,
                ProductSubcategory.is_deleted == False,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A subcategory '{update_data['name']}' already exists under this category.",
            )

    for key, value in update_data.items():
        setattr(subcategory, key, value)

    db.commit()
    db.refresh(subcategory)

    return _build_response(subcategory)


# ==========================================
# 5. SOFT DELETE PRODUCT SUBCATEGORY (Admin Only)
# ==========================================
@router.delete("/{subcategory_id}")
def delete_product_subcategory(
    subcategory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    subcategory = (
        db.query(ProductSubcategory)
        .filter(ProductSubcategory.id == subcategory_id)
        .first()
    )
    if not subcategory or subcategory.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subcategory not found.",
        )

    subcategory.is_deleted = True
    subcategory.is_active = False
    db.commit()

    return {
        "success": True,
        "message": f"Subcategory '{subcategory.name}' has been soft deleted.",
    }
