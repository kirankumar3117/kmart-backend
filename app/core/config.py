from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Kirana"
    DATABASE_URL: str
    
    # --- ADD THESE 3 LINES FOR SECURITY ---
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # Token lasts for 7 days

    class Config:
        env_file = ".env"

settings = Settings()