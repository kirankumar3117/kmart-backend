from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.models.shop_category import ShopCategory
from app.models.product_category import ProductCategory
from app.models.user import User
from app.schemas.category import ShopCategoryListResponse, ShopCategoryUpdate, ShopCategoryResponse
from app.utils.auth import get_current_user

router = APIRouter()

# ==========================================
# 1. LIST ALL SHOP CATEGORIES (Public)
# ==========================================
@router.get("/shop-categories", response_model=ShopCategoryListResponse)
def get_shop_categories(db: Session = Depends(get_db)):
    categories = db.query(ShopCategory).order_by(ShopCategory.name.asc()).all()
    return ShopCategoryListResponse(success=True, data=categories)


# ==========================================
# 2. UPDATE SHOP CATEGORY (Admin Only)
# ==========================================
@router.patch("/shop-categories/{category_id}", response_model=ShopCategoryResponse)
def update_shop_category(
    category_id: UUID,
    body: ShopCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Admin only
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    # 2. Find the category
    shop_cat = db.query(ShopCategory).filter(ShopCategory.id == category_id).first()
    if not shop_cat:
        raise HTTPException(status_code=404, detail="Shop category not found.")

    # 3. Update basic fields
    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data:
        shop_cat.name = update_data["name"]
    if "description" in update_data:
        shop_cat.description = update_data["description"]

    # 4. Update Product Category links
    if "product_category_ids" in update_data:
        pc_ids = update_data["product_category_ids"]
        product_cats = db.query(ProductCategory).filter(ProductCategory.id.in_(pc_ids)).all()
        if len(product_cats) != len(pc_ids):
            raise HTTPException(status_code=400, detail="One or more Product Category IDs are invalid.")
        
        shop_cat.product_categories = product_cats

    db.commit()
    db.refresh(shop_cat)
    return shop_cat
