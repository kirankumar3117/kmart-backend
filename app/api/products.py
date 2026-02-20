from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse

router = APIRouter()

# 1. CREATE PRODUCT (Admin Side)
@router.post("/", response_model=ProductResponse)
def create_product(item: ProductCreate, db: Session = Depends(get_db)):
    # Check for duplicate barcode if provided
    if item.barcode:
        existing = db.query(Product).filter(Product.barcode == item.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Product with this barcode exists")
    
    db_product = Product(**item.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

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