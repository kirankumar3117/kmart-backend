from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserStatusUpdate, FCMTokenUpdate
from app.utils.auth import get_current_user

router = APIRouter()

@router.patch("/{user_id}/status")
def update_user_status(user_id: UUID, body: UserStatusUpdate, db: Session = Depends(get_db)):
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
            "user_id": str(user.id),
            "is_active": user.is_active
        }
    }


@router.patch("/fcm-token")
def update_fcm_token(
    body: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mobile app calls this on launch to register its FCM push token."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.fcm_token = body.fcm_token
    db.commit()
    
    return {"success": True, "message": "FCM token updated successfully"}
