from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.shop_category import ShopCategory
from app.schemas.category import ShopCategoryListResponse

router = APIRouter()

@router.get("/shop-categories", response_model=ShopCategoryListResponse)
def get_shop_categories(db: Session = Depends(get_db)):
    categories = db.query(ShopCategory).order_by(ShopCategory.name.asc()).all()
    return ShopCategoryListResponse(success=True, data=categories)
