from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.utils.auth import get_current_user
from app.models.user import User, UserRole
from app.models.shop import Shop, OnboardingStep
from app.models.agent import Agent
from app.models.shop_category import ShopCategory
from app.schemas.agent import AgentOnboardMerchantRequest, AgentStatusUpdate, AgentCreate
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()

class AgentLoginRequest(BaseModel):
    login_id: str = Field(..., description="Phone number or Agent Code")
    pin: str = Field(..., min_length=4, max_length=4)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only Admin can create agents
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can create new Agents."
        )

    # 1. Check if Agent Code exists
    existing_agent_code = db.query(Agent).filter(Agent.agent_code == body.agent_code).first()
    if existing_agent_code:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent code '{body.agent_code}' is already in use."
        )

    # 2. Check if the User structure (phone/email per role) already exists
    existing_user_phone = db.query(User).filter(User.phone_number == body.phone, User.role == "agent").first()
    if existing_user_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An agent with phone number '{body.phone}' already exists."
        )

    if body.email:
        existing_user_email = db.query(User).filter(User.email == body.email, User.role == "agent").first()
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An agent with email '{body.email}' already exists."
            )

    # 3. Create Agent record
    new_agent = Agent(
        name=body.name,
        agent_code=body.agent_code,
        phone=body.phone,
        is_active=True
    )
    db.add(new_agent)

    # 4. Create User record for the agent to login
    hashed_pin = get_password_hash(body.pin)
    new_user = User(
        full_name=body.name,
        phone_number=body.phone,
        email=body.email,
        hashed_pin=hashed_pin,
        role="agent",
        is_verified=True,
        onboarding_step=OnboardingStep.COMPLETED,
    )
    db.add(new_user)
    
    db.commit()
    db.refresh(new_agent)

    return {
        "success": True,
        "message": "Agent created successfully",
        "data": {
            "agent_id": str(new_agent.id),
            "agent_code": new_agent.agent_code,
            "name": new_agent.name
        }
    }


@router.post("/login")
def login_agent(body: AgentLoginRequest, db: Session = Depends(get_db)):
    # The login_id can be a phone number or an agent_code.
    # We must find the User with role = 'agent'.
    # If the login_id looks like a phone number we search by phone_number,
    # otherwise we might need to look up the agent_code in Agent table to get their phone number, 
    # but the simplest way is to ensure `User.phone_number == login_id` because agent uses their phone.
    # If they use agent code, we find the agent, get their phone, then find the User.
    
    agent_phone = body.login_id
    
    if not body.login_id.isdigit():
        # Probably an agent code like AGENT007
        agent = db.query(Agent).filter(Agent.agent_code == body.login_id).first()
        if not agent or not agent.phone:
            raise HTTPException(status_code=401, detail="Invalid Agent Code")
        agent_phone = agent.phone

    user = db.query(User).filter(
        User.phone_number == agent_phone,
        User.role == "agent"
    ).first()

    if not user or not user.hashed_pin or not verify_password(body.pin, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number, agent code, or PIN"
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Agent account is inactive")

    access_token = create_access_token(data={"sub": str(user.id), "role": "agent"})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


@router.post("/onboard-shop")
async def onboard_shop_by_agent(
    request: AgentOnboardMerchantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify that the current user is an agent
    if current_user.role.lower() != "agent" and current_user.role.upper() != UserRole.AGENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents can perform this action"
        )

    # 1.5. Validate Agent Code matches current agent (Optional safety step, since token already proves identity)
    # We'll just verify the agent exists and active
    agent_record = None
    if request.agent_code:
        agent_record = db.query(Agent).filter(Agent.agent_code == request.agent_code).first()
    else:
        agent_record = db.query(Agent).filter(Agent.phone == current_user.phone_number).first()

    if not agent_record or not agent_record.is_active:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive agent code"
        )

    # 1.6 Validate Shop Category
    category_record = db.query(ShopCategory).filter(ShopCategory.id == request.shop_category_id).first()
    if not category_record:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shop category ID"
        )

    # 2. Check if the user already exists *WITH THIS ROLE*
    target_role = request.role.lower() if request.role else "merchant"
    existing_user = db.query(User).filter(
        User.phone_number == request.phone_number,
        User.role == target_role
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered. Please use a different phone number."
        )

    # 2.5 Check if the shop phone number already exists
    existing_shop = db.query(Shop).filter(Shop.phone == request.phone_number).first()
    if existing_shop:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shop with this phone number already exists. Please use a different phone number."
        )

    if request.email:
        existing_user_email = db.query(User).filter(
            User.email == request.email,
            User.role == target_role
        ).first()
        if existing_user_email:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A user with this email already exists as a {target_role}"
            )

    # 3. Hash the PIN
    hashed_pin = get_password_hash(request.pin)

    # 4. Create the User (Merchant)
    # Using 'merchant' as the role string 
    db_role_mapping = "merchant" if target_role == "merchant" else target_role

    new_user = User(
        full_name=request.merchant_name,
        phone_number=request.phone_number,
        email=request.email,
        hashed_pin=hashed_pin,
        role=db_role_mapping,  
        onboarding_step=OnboardingStep.COMPLETED,
        is_verified=True # Assuming the agent has verified them
    )
    db.add(new_user)
    db.flush() # Get the new_user.id without committing

    # 5. Create the Shop
    new_shop = Shop(
        owner_id=new_user.id,
        category_id=category_record.id,
        onboarded_by_agent_id=current_user.id,
        agent_id=agent_record.id,
        shop_name=request.shop_name,
        owner_name=request.merchant_name,
        phone=request.phone_number,
        email=request.email,
        address=request.shop_location,
        shop_image_url=request.shop_image_url,
        owner_image_url=request.merchant_image_url,
        is_verified=True,
        is_onboarded=True,
        onboarding_step=OnboardingStep.COMPLETED,
    )
    db.add(new_shop)

    # 6. Commit the transaction
    db.commit()
    db.refresh(new_shop)

    return {
        "success": True,
        "message": "Merchant and shop successfully onboarded",
        "data": {
            "shop_id": str(new_shop.id),
            "user_id": new_user.id,
            "agent_code": agent_record.agent_code if agent_record else None
        }
    }


@router.patch("/{agent_id}/status")
def update_agent_status(agent_id: str, body: AgentStatusUpdate, db: Session = Depends(get_db)):
    # 1. Update the Agent record
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    agent.is_active = body.is_active
    db.commit()
    db.refresh(agent)

    # 2. Also find and update the associated User record so they can't log in
    if agent.phone:
        user = db.query(User).filter(User.phone_number == agent.phone, User.role == "agent").first()
        if user:
            user.is_active = body.is_active
            db.commit()
            db.refresh(user)

    return {
        "success": True,
        "message": f"Agent status updated to {'active' if body.is_active else 'inactive'}",
        "data": {
            "agent_id": str(agent.id),
            "is_active": agent.is_active
        }
    }
