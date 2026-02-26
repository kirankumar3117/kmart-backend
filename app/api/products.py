from app.utils.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse

router = APIRouter()

# ==========================================
# CREATE MASTER PRODUCT (Protected: Admin Only)
# ==========================================
@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- Require Token
):
    # 1. Strict Role Check: Only admins can touch the master catalog
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can add master products."
        )
        
    # 2. Check for duplicate barcode if provided
    if product.barcode:
        existing = db.query(Product).filter(Product.barcode == product.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Product with this barcode already exists.")

    new_product = Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return new_product

# 2. SEARCH / LIST PRODUCTS (Customer Side)
# Usage: /products?search=soap&category=Personal Care
@router.get("/", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)

    if search:
        # Case-insensitive search (ILIKE in Postgres)
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    if category and category != "All":
        query = query.filter(Product.category == category)
        
    return query.offset(skip).limit(limit).all()