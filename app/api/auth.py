from app.schemas.user import UserLogin
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse # <--- New Import
from app.core.security import verify_password, create_access_token, get_password_hash # <--- Added hash import

router = APIRouter()

# ==========================================
# REGISTER NEW USER
# ==========================================
@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if the phone number is already registered (This is our main check now)
    existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # 2. Only check for duplicate email IF they actually provided one
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    # 3. Create the user
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        email=user_data.email,
        hashed_password=hashed_pwd,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post("/login")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # 1. Find user by BOTH phone number AND their role
    user = db.query(User).filter(
        User.phone_number == login_data.phone_number,
        User.role == login_data.role # <--- Now checking the role too!
    ).first()
    
    # 2. Verify password
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number, password, or role",
        )
        
    # 3. Generate the token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # 4. Return the standard token format
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user.role 
    }