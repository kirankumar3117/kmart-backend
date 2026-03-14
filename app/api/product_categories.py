from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.product_category import ProductCategory
from app.models.user import User
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCategoryResponse,
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
            detail="Only admins can manage product categories.",
        )


# ==========================================
# 1. CREATE PRODUCT CATEGORY (Admin Only)
# ==========================================
@router.post("/", response_model=ProductCategoryResponse, status_code=201)
def create_product_category(
    body: ProductCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    # Check duplicate name
    existing = db.query(ProductCategory).filter(ProductCategory.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        )

    new_category = ProductCategory(**body.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


# ==========================================
# 2. LIST ALL PRODUCT CATEGORIES (Public)
# ==========================================
@router.get("/", response_model=List[ProductCategoryResponse])
def list_product_categories(db: Session = Depends(get_db)):
    categories = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.is_active == True,
            ProductCategory.is_deleted == False,
        )
        .order_by(ProductCategory.name.asc())
        .all()
    )
    return categories


# ==========================================
# 3. UPDATE PRODUCT CATEGORY (Admin Only)
# ==========================================
@router.patch("/{category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    category_id: int,
    body: ProductCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category or category.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    # Check duplicate name if name is being changed
    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = (
            db.query(ProductCategory)
            .filter(ProductCategory.name == update_data["name"], ProductCategory.id != category_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists.",
            )

    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


# ==========================================
# 4. SOFT DELETE PRODUCT CATEGORY (Admin Only)
# ==========================================
@router.delete("/{category_id}")
def delete_product_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category or category.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    category.is_deleted = True
    category.is_active = False
    db.commit()

    return {
        "success": True,
        "message": f"Category '{category.name}' has been soft deleted.",
    }
