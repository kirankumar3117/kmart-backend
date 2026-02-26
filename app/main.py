from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Import Routers
from app.api import auth, products, shops, inventory, orders, upload, ws, onboarding

# ==========================================
# THE "UNUSED" IMPORTS (Model Registration)
# ==========================================
# We import these files so SQLAlchemy reads them and registers them to Base.metadata
from app.models import user, product, shop, inventory as model_inventory, order, cart_suggestion, agent

# ==========================================
# TABLE MIGRATIONS (Powered by Alembic)
# ==========================================
# Previously: Base.metadata.create_all(bind=engine)
# Now we use Alembic! Run migrations with:
#   alembic revision --autogenerate -m "describe your change"
#   alembic upgrade head

app = FastAPI(title=settings.PROJECT_NAME)


# ==========================================
# CORS SETUP (Crucial for Mobile/Web Apps)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change "*" to your actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PATCH, etc.
    allow_headers=["*"],  # Allows all headers (like our Authorization Bearer token)
)

# ==========================================
# FILE UPLOADS SETUP
# ==========================================
# 1. Create the 'uploads' folder on your Mac if it doesn't exist yet
os.makedirs("uploads", exist_ok=True)

# 2. Tell FastAPI to serve files from this folder at the "/static" URL
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# ==========================================
# REGISTER ROUTES
# ==========================================
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(shops.router, prefix="/api/v1/shops", tags=["Shops"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Uploads"])

# Onboarding routes (register, setup, status)
app.include_router(onboarding.router, prefix="/api/v1/shops", tags=["Onboarding"])

# ==========================================
# WEBSOCKET ROUTES (Real-time updates)
# ==========================================
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])