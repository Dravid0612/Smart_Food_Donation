from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.models import User, VolunteerAssignment, FoodDonation, Notification
from app.schemas.schemas import UserResponse, VolunteerAssignmentResponse
from app.core.dependencies import get_current_user, require_role

router = APIRouter(prefix="/volunteers", tags=["Volunteers"])

@router.get("", response_model=List[UserResponse])
def get_volunteers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    return volunteers

@router.get("/available", response_model=List[UserResponse])
def get_available_volunteers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Returns active volunteers who currently have less than 3 active assignments
    all_vols = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    available = []
    for vol in all_vols:
        active_count = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.volunteer_id == vol.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "collected"])
        ).count()
        if active_count < 3:
            available.append(vol)
    return available

@router.post("/assignments", response_model=VolunteerAssignmentResponse)
def create_volunteer_assignment(
    donation_id: int,
    volunteer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    volunteer = db.query(User).filter(User.id == volunteer_id, User.role == "volunteer").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer user not found.")

    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer.id,
        status="assigned"
    )
    db.add(assignment)

    donation.assigned_volunteer_id = volunteer.id
    donation.status = "volunteer_assigned"

    # Notify Volunteer
    notification = Notification(
        user_id=volunteer.id,
        title="New Pickup Assignment",
        message=f"You have been assigned to pick up '{donation.food_name}' at {donation.pickup_address}.",
        type="assignment",
        related_donation_id=donation.id
    )
    db.add(notification)

    db.commit()
    db.refresh(assignment)
    return assignment

@router.put("/assignments/{assignment_id}", response_model=VolunteerAssignmentResponse)
def update_volunteer_assignment_status(
    assignment_id: int,
    status_update: str, # accepted, collected, delivered, cancelled
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "ngo", "admin"]))
):
    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    now = datetime.now(timezone.utc)
    assignment.status = status_update.lower()

    if status_update.lower() == "accepted":
        assignment.accepted_at = now
    elif status_update.lower() == "collected":
        assignment.collected_at = now
    elif status_update.lower() == "delivered":
        assignment.delivered_at = now

    db.commit()
    db.refresh(assignment)
    return assignment
