from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Import Routers
from app.api import auth, products, shops, inventory, orders, upload, ws 

# ==========================================
# THE "UNUSED" IMPORTS (Model Registration)
# ==========================================
# We import these files so SQLAlchemy reads them and registers them to Base.metadata
from app.models import user, product, shop, inventory as model_inventory, order 

# Create Tables (Auto-Migration)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

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

# ==========================================
# WEBSOCKET ROUTES (Real-time updates)
# ==========================================
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])