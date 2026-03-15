from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import os

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Import Routers
from app.api import products, product_categories, shops, inventory, orders, upload, ws, agents, categories, customer_auth, merchant_auth, admin_auth, users

# ==========================================
# THE "UNUSED" IMPORTS (Model Registration)
# ==========================================
# We import these files so SQLAlchemy reads them and registers them to Base.metadata
from app.models import user, product, product_category, shop, inventory as model_inventory, order, cart_suggestion, agent

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
# GLOBAL ERROR HANDLERS
# Override FastAPI defaults so all errors return a flat, consistent shape:
#   { "success": false, "message": "...", "code": "..." }
# ==========================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # FastAPI's default returns an array of error objects.
    # We flatten it to a single human-readable message string.
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = " → ".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        msg = first.get("msg", "Validation error")
        message = f"{field}: {msg}" if field else msg
    else:
        message = "Invalid request data"

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": message,
            "code": "VALIDATION_ERROR",
        },
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
app.include_router(customer_auth.router, prefix="/api/v1/auth/customer", tags=["Customer Authentication"])
app.include_router(merchant_auth.router, prefix="/api/v1/auth/merchant", tags=["Merchant Authentication"])
app.include_router(admin_auth.router, prefix="/api/v1/auth/admin", tags=["Admin Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(product_categories.router, prefix="/api/v1/product-categories", tags=["Product Categories"])
app.include_router(shops.router, prefix="/api/v1/shops", tags=["Shops"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Uploads"])

# Shop Categories
app.include_router(categories.router, prefix="/api/v1", tags=["Categories"])

# Agent Operations
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])


# ==========================================
# WEBSOCKET ROUTES (Real-time updates)
# ==========================================
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])