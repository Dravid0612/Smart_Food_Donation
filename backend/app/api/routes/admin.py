from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.db.session import get_db
from app.models.models import User, NGO, FoodDonation
from app.schemas.schemas import AdminStatsResponse, UserResponse, NGOResponse, DonationResponse
from app.core.dependencies import require_role
from app.services.urgency_service import calculate_urgency

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/statistics", response_model=AdminStatsResponse)
def get_admin_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    total_users = db.query(User).count()
    total_donors = db.query(User).filter(User.role == "donor").count()
    total_ngos = db.query(NGO).count()
    total_volunteers = db.query(User).filter(User.role == "volunteer").count()
    total_donations = db.query(FoodDonation).count()
    completed_donations = db.query(FoodDonation).filter(FoodDonation.status == "completed").count()
    pending_donations = db.query(FoodDonation).filter(FoodDonation.status == "pending").count()
    unverified_ngos = db.query(NGO).filter(NGO.is_verified == False).count()

    meals = db.query(func.sum(FoodDonation.quantity)).filter(
        FoodDonation.status.in_(["delivered", "completed"])
    ).scalar() or 0.0

    return AdminStatsResponse(
        total_users=total_users,
        total_donors=total_donors,
        total_ngos=total_ngos,
        total_volunteers=total_volunteers,
        total_donations=total_donations,
        completed_donations=completed_donations,
        pending_donations=pending_donations,
        meals_donated=float(meals),
        unverified_ngos=unverified_ngos
    )

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    return db.query(User).order_by(User.created_at.desc()).all()

@router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account.")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user

@router.get("/donations", response_model=List[DonationResponse])
def get_all_admin_donations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    donations = db.query(FoodDonation).order_by(FoodDonation.created_at.desc()).all()
    res = []
    for d in donations:
        item = DonationResponse.model_validate(d)
        item.urgency_level = calculate_urgency(d.preparation_time, d.expiry_time)
        res.append(item)
    return res

@router.get("/ngos", response_model=List[NGOResponse])
def get_all_admin_ngos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    return db.query(NGO).all()

@router.get("/waste-heatmap")
def get_waste_heatmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Returns spatial cluster density data for surplus food heatmap visualization."""
    donations = db.query(FoodDonation).all()
    grid_map = {}

    for d in donations:
        if d.latitude and d.longitude:
            # Round coordinates to ~1km grid cells (2 decimal places)
            lat_grid = round(d.latitude, 2)
            lon_grid = round(d.longitude, 2)
            key = f"{lat_grid},{lon_grid}"

            if key not in grid_map:
                grid_map[key] = {
                    "latitude": lat_grid,
                    "longitude": lon_grid,
                    "total_donations": 0,
                    "total_meals": 0.0,
                    "active_urgent_count": 0
                }

            grid_map[key]["total_donations"] += 1
            grid_map[key]["total_meals"] += float(d.quantity)
            if calculate_urgency(d.preparation_time, d.expiry_time) == "Urgent":
                grid_map[key]["active_urgent_count"] += 1

    heatmap_points = list(grid_map.values())
    return {
        "clusters": heatmap_points,
        "total_clusters": len(heatmap_points),
        "total_impacted_meals": sum(p["total_meals"] for p in heatmap_points)
    }

