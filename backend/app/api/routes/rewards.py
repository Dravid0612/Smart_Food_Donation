from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import RewardResponse
from app.core.dependencies import get_current_user
from app.services.reward_service import get_reward_details

router = APIRouter(prefix="/rewards", tags=["Rewards"])

@router.get("/me", response_model=RewardResponse)
def get_my_rewards(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_reward_details(db, current_user.id)
