from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token
from app.models.models import User, NGO, Reward
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered."
        )

    # Hash password
    hashed_pwd = hash_password(user_in.password)

    # Create User
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_pwd,
        phone=user_in.phone,
        role=user_in.role.lower(),
        address=user_in.address,
        latitude=user_in.latitude,
        longitude=user_in.longitude
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If role is NGO, create NGO profile
    if new_user.role == "ngo":
        ngo_profile = NGO(
            user_id=new_user.id,
            organization_name=user_in.organization_name or user_in.name,
            description=user_in.description or "Community food support organization",
            address=user_in.address,
            latitude=user_in.latitude,
            longitude=user_in.longitude,
            capacity=user_in.capacity or 100,
            current_capacity=user_in.capacity or 100,
            contact_phone=user_in.phone,
            is_verified=False
        )
        db.add(ngo_profile)

    # If role is Donor, initialize Reward record
    if new_user.role == "donor":
        reward = Reward(user_id=new_user.id, points=0, level="Bronze")
        db.add(reward)

    db.commit()
    return new_user

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact administrator."
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        name=user.name,
        email=user.email
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
