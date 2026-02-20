from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kmart API"
    API_V1_STR: str = "/api/v1"
    
    # DATABASE URL (We will fill this in Phase 2)
    # Format: postgresql://user:password@localhost/dbname
    DATABASE_URL: str = "postgresql://postgres:admin123@localhost:5432/kmart_db"

    class Config:
        env_file = ".env"

settings = Settings()