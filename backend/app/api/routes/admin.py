from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.donation import FoodDonation
from app.models.ngo import NGO
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, int]:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    total_users = db.query(User).count()
    total_ngos = db.query(User).filter(User.role == "ngo").count()
    total_donations = db.query(FoodDonation).count()
    pending_donations = db.query(FoodDonation).filter(FoodDonation.status == "pending").count()
    completed_donations = db.query(FoodDonation).filter(FoodDonation.status == "completed").count()

    return {
        "total_users": total_users,
        "total_ngos": total_ngos,
        "total_donations": total_donations,
        "pending_donations": pending_donations,
        "completed_donations": completed_donations,
    }
