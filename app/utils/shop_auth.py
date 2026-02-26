from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.shop import Shop

# Reuse the same Bearer scheme
security = HTTPBearer()


def get_current_shop(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Shop:
    """
    JWT dependency for shop-based authentication.
    Decodes the token where 'sub' = shop UUID string,
    returns the Shop ORM object.
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        shop_id: str = payload.get("sub")
        if shop_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if shop is None:
        raise credentials_exception

    return shop
