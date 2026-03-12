import os
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.shop_category import ShopCategory

categories = [
    "Kirana Store",
    "Juice Shop",
    "Biryani Point",
    "Tiffin Center",
    "Medical Store",
    "Bakery",
    "Fast Food Center",
    "Supermarket"
]

def seed():
    db: Session = SessionLocal()
    try:
        for cat_name in categories:
            # Check if exists
            existing = db.query(ShopCategory).filter(ShopCategory.name == cat_name).first()
            if not existing:
                new_cat = ShopCategory(name=cat_name, description=f"{cat_name} category")
                db.add(new_cat)
        db.commit()
        print("Successfully seeded shop categories!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding categories: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
