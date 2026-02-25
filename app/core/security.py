from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Tells passlib we want to use the industry-standard bcrypt hashing algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. Scramble the password before saving to the database
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# 2. Check if the plain password matches the scrambled one in the database
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 3. Create the Digital ID Card (JWT)
def create_access_token(data: dict):
    to_encode = data.copy()
    
    # Calculate when the token should expire
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Sign the token using our Secret Key
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt