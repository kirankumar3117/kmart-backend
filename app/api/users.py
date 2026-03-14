from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserStatusUpdate

router = APIRouter()

@router.patch("/{user_id}/status")
def update_user_status(user_id: int, body: UserStatusUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": f"User status updated to {'active' if body.is_active else 'inactive'}",
        "data": {
            "user_id": user.id,
            "is_active": user.is_active
        }
    }
