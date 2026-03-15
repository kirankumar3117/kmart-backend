import os
import sys
import argparse
from sqlalchemy.orm import Session

# Add the project root to the python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.shop_category import ShopCategory

# Define the categories to seed
CATEGORIES = [
    "Kirana Store",
    "Juice Shop",
    "Biryani Point",
    "Tiffin Center",
    "Medical Store",
    "Bakery",
    "Fast Food Center",
    "Supermarket"
]

def seed_categories(db: Session):
    for cat_name in CATEGORIES:
        existing = db.query(ShopCategory).filter(ShopCategory.name == cat_name).first()
        if not existing:
            new_cat = ShopCategory(name=cat_name, description=f"{cat_name} category")
            db.add(new_cat)
    db.commit()
    print("[+] Successfully seeded shop categories!")


def seed():
    db = SessionLocal()
    try:
        print("🌱 Starting database seeding process...\n")
        print("➡️ Seeding Categories...")
        seed_categories(db)
        print("\n🎉 Seeding process complete!")
    except Exception as e:
        db.rollback()
        print(f"[!] Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database with Categories.")
    args = parser.parse_args()
    seed()
