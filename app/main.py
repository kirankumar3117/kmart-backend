from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Import Routers
from app.api import auth, products  # <--- IMPORT THIS

# Create Tables (Auto-Migration)
from app.models import user, product # <--- IMPORT MODEL HERE TO CREATE TABLE
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# Register Routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"]) # <--- ADD THIS