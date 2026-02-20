from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 1. Create the Engine (The connection to Postgres)
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# 2. Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Dependency (We use this in every API route)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()