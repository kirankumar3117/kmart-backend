from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Kirana"
    DATABASE_URL: str
    
    # --- SECURITY SETTINGS ---
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # Access token lasts 1 day (24 hours)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # Refresh token lasts 30 days
    
    # --- ADMIN CREATION ---
    ADMIN_CREATION_SECRET: str
    
    # --- CRON SECRETS ---
    CRON_SECRET: str = "test-cron-secret-change-in-production"

    class Config:
        env_file = ".env"

settings = Settings()