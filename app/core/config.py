from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kmart API"
    API_V1_STR: str = "/api/v1"
    
    # By defining the type but NOT giving it a string, 
    # Pydantic is forced to go look in the .env file for this exact variable name!
    DATABASE_URL: str 

    class Config:
        env_file = ".env"

settings = Settings()