from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.models import (
    FoodDonation, DonationHistory, NGO, User, VolunteerAssignment, Notification
)
from app.schemas.schemas import (
    DonationCreate, DonationUpdate, DonationResponse, DonationDetailResponse,
    NGORecommendationResponse, VolunteerRecommendationResponse
)
from app.core.dependencies import get_current_user, require_role
from app.services.urgency_service import calculate_urgency
from app.services.recommendation_service import recommend_ngos, recommend_volunteers
from app.services.reward_service import add_reward_points
from app.services.notification_service import create_notification

router = APIRouter(prefix="/donations", tags=["Donations"])

def log_status_change(db: Session, donation_id: int, old_status: str, new_status: str, changed_by: int, remarks: str = ""):
    history = DonationHistory(
        donation_id=donation_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        remarks=remarks
    )
    db.add(history)
    db.flush()

@router.post("", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def create_donation(
    donation_in: DonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    if donation_in.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero.")

    now = datetime.now(timezone.utc)
    expiry = donation_in.expiry_time
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        raise HTTPException(status_code=400, detail="Expiry time must be in the future.")

    new_donation = FoodDonation(
        donor_id=current_user.id,
        food_name=donation_in.food_name,
        description=donation_in.description,
        food_category=donation_in.food_category,
        quantity=donation_in.quantity,
        quantity_unit=donation_in.quantity_unit,
        preparation_time=donation_in.preparation_time,
        expiry_time=donation_in.expiry_time,
        pickup_address=donation_in.pickup_address,
        latitude=donation_in.latitude or current_user.latitude or 12.9716,
        longitude=donation_in.longitude or current_user.longitude or 77.5946,
        image_url=donation_in.image_url,
        status="pending"
    )
    db.add(new_donation)
    db.commit()
    db.refresh(new_donation)

    log_status_change(db, new_donation.id, None, "pending", current_user.id, "Donation created")
    
    # Notify active NGOs
    ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()
    for ngo in ngos:
        create_notification(
            db,
            user_id=ngo.user_id,
            title="New Food Donation Available",
            message=f"New donation '{new_donation.food_name}' ({new_donation.quantity} {new_donation.quantity_unit}) posted nearby.",
            type="donation",
            related_donation_id=new_donation.id
        )

    db.commit()
    
    response_data = DonationResponse.model_validate(new_donation)
    response_data.urgency_level = calculate_urgency(new_donation.preparation_time, new_donation.expiry_time)
    return response_data

@router.get("", response_model=List[DonationResponse])
def get_donations(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    my_donations_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(FoodDonation)

    if current_user.role == "donor" or my_donations_only:
        query = query.filter(FoodDonation.donor_id == current_user.id)
    elif current_user.role == "ngo":
        # NGO can see available pending donations or donations assigned to them
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        ngo_id = ngo_profile.id if ngo_profile else -1
        query = query.filter(
            (FoodDonation.status == "pending") | (FoodDonation.assigned_ngo_id == ngo_id)
        )
    elif current_user.role == "volunteer":
        # Volunteer sees assigned pickups or available accepted donations needing volunteer
        query = query.filter(
            (FoodDonation.assigned_volunteer_id == current_user.id) |
            (FoodDonation.status == "accepted")
        )

    if status_filter:
        query = query.filter(FoodDonation.status == status_filter)
    if category_filter:
        query = query.filter(FoodDonation.food_category == category_filter)

    donations = query.order_by(FoodDonation.created_at.desc()).all()
    result = []
    for d in donations:
        item = DonationResponse.model_validate(d)
        item.urgency_level = calculate_urgency(d.preparation_time, d.expiry_time)
        result.append(item)
    return result

@router.get("/{donation_id}", response_model=DonationDetailResponse)
def get_donation_detail(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    donor = db.query(User).filter(User.id == donation.donor_id).first()
    ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first() if donation.assigned_ngo_id else None
    volunteer = db.query(User).filter(User.id == donation.assigned_volunteer_id).first() if donation.assigned_volunteer_id else None

    detail = DonationDetailResponse.model_validate(donation)
    detail.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    detail.donor_name = donor.name if donor else None
    detail.donor_phone = donor.phone if donor else None
    detail.ngo_name = ngo.organization_name if ngo else None
    detail.volunteer_name = volunteer.name if volunteer else None
    detail.volunteer_phone = volunteer.phone if volunteer else None
    detail.history = [DonationHistoryResponse.model_validate(h) for h in donation.history]
    return detail

@router.post("/{donation_id}/accept", response_model=DonationResponse)
def accept_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    if donation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Donation is already in status '{donation.status}'.")

    ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
    if not ngo_profile:
        raise HTTPException(status_code=400, detail="NGO profile not found.")

    old_status = donation.status
    donation.status = "accepted"
    donation.assigned_ngo_id = ngo_profile.id
    
    # Deduct capacity
    if ngo_profile.current_capacity >= donation.quantity:
        ngo_profile.current_capacity -= int(donation.quantity)

    log_status_change(db, donation.id, old_status, "accepted", current_user.id, f"Accepted by {ngo_profile.organization_name}")

    # Notify donor
    create_notification(
        db,
        user_id=donation.donor_id,
        title="Donation Accepted",
        message=f"Your donation '{donation.food_name}' has been accepted by {ngo_profile.organization_name}.",
        type="success",
        related_donation_id=donation.id
    )

    db.commit()
    db.refresh(donation)

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/reject", response_model=DonationResponse)
def reject_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    old_status = donation.status
    donation.status = "rejected"
    log_status_change(db, donation.id, old_status, "rejected", current_user.id, "Rejected by NGO")

    db.commit()
    db.refresh(donation)
    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/collect", response_model=DonationResponse)
def collect_food(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    old_status = donation.status
    donation.status = "collected"
    log_status_change(db, donation.id, old_status, "collected", current_user.id, "Food collected by volunteer")

    # Update assignment
    assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.volunteer_id == current_user.id
    ).first()
    if assignment:
        assignment.collected_at = datetime.now(timezone.utc)
        assignment.status = "collected"

    # Notify Donor and NGO
    create_notification(db, donation.donor_id, "Food Collected", f"Volunteer has picked up '{donation.food_name}'.", "info", donation.id)
    if donation.assigned_ngo and donation.assigned_ngo.user_id:
        create_notification(db, donation.assigned_ngo.user_id, "Delivery En Route", f"Volunteer is delivering '{donation.food_name}'.", "info", donation.id)

    db.commit()
    db.refresh(donation)
    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/deliver", response_model=DonationResponse)
def deliver_food(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "ngo", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    old_status = donation.status
    donation.status = "completed"
    log_status_change(db, donation.id, old_status, "completed", current_user.id, "Food successfully delivered & completed")

    # Update assignment
    assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id
    ).first()
    if assignment:
        assignment.delivered_at = datetime.now(timezone.utc)
        assignment.status = "delivered"

    # Award Donor Reward Points (+10)
    add_reward_points(db, donation.donor_id, points_to_add=10)

    # Send Notification to Donor
    create_notification(
        db,
        user_id=donation.donor_id,
        title="Donation Completed! 🎉",
        message=f"Your donation '{donation.food_name}' was successfully delivered! You earned +10 reward points.",
        type="success",
        related_donation_id=donation.id
    )

    db.commit()
    db.refresh(donation)
    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.get("/{donation_id}/recommend-ngo", response_model=List[NGORecommendationResponse])
def get_ngo_recommendations(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return recommend_ngos(db, donation)

@router.get("/{donation_id}/recommend-volunteer", response_model=List[VolunteerRecommendationResponse])
def get_volunteer_recommendations(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return recommend_volunteers(db, donation)
