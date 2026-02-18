from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend for Kmart Customer & Shopkeeper Apps",
    version="1.0.0"
)

# 1. Basic Health Check Route
@app.get("/")
def read_root():
    return {"message": "Welcome to Kmart API", "status": "active"}

# 2. Test Route to verify it works
@app.get("/ping")
def ping():
    return {"ping": "pong!"}