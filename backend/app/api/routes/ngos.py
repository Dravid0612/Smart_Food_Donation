import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.models import NGO, User, FoodDonation, MatchOffer
from app.schemas.schemas import (
    NGOResponse, NGOUpdate, NGOOperatingHoursUpdate, NGODemandUpdate,
    MatchOfferResponse, DonationResponse
)
from app.core.dependencies import get_current_user, require_role
from app.services.urgency_service import calculate_urgency

router = APIRouter(prefix="/ngos", tags=["NGOs"])

@router.get("", response_model=List[NGOResponse])
def get_ngos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ngos = db.query(NGO).all()
    return ngos

@router.get("/me", response_model=NGOResponse)
def get_my_ngo(db: Session = Depends(get_db), current_user: User = Depends(require_role(["ngo", "admin"]))):
    ngo = db.query(NGO).filter(NGO.user_id == current_user.id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO profile not found for current user.")
    return ngo

@router.get("/me/offers", response_model=List[MatchOfferResponse])
def get_my_ngo_offers(
    status_filter: Optional[str] = Query(None, description="Optional status filter ('offered', 'accepted', 'cancelled')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    """Returns rescue match offers dispatched to this authenticated NGO."""
    query = db.query(MatchOffer).filter(
        MatchOffer.candidate_id == current_user.id,
        MatchOffer.candidate_type == "ngo"
    )
    if status_filter:
        query = query.filter(MatchOffer.status == status_filter)
    return query.order_by(MatchOffer.offered_at.desc()).all()

@router.get("/me/self-pickups", response_model=List[DonationResponse])
def get_my_ngo_self_pickups(
    status_filter: Optional[str] = Query(None, description="Filter by status (e.g. accepted, collected)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    """Returns donations assigned to this NGO for direct self-pickup."""
    ngo = db.query(NGO).filter(NGO.user_id == current_user.id).first()
    if not ngo and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="NGO profile not found for current user.")
    
    query = db.query(FoodDonation).filter(FoodDonation.pickup_mode == "self_pickup")
    if current_user.role == "ngo" and ngo:
        query = query.filter(FoodDonation.assigned_ngo_id == ngo.id)
    if status_filter:
        query = query.filter(FoodDonation.status == status_filter)
    
    donations = query.order_by(FoodDonation.created_at.desc()).all()
    results = []
    for d in donations:
        item = DonationResponse.model_validate(d)
        item.urgency_level = calculate_urgency(d.preparation_time, d.expiry_time)
        results.append(item)
    return results

@router.get("/{ngo_id}", response_model=NGOResponse)
def get_ngo_by_id(ngo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found.")
    return ngo

@router.put("/{ngo_id}", response_model=NGOResponse)
def update_ngo(
    ngo_id: int,
    ngo_in: NGOUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found.")

    # Authorization: Only NGO owner or Admin can edit
    if current_user.role != "admin" and ngo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this NGO profile.")

    for field, value in ngo_in.model_dump(exclude_unset=True).items():
        setattr(ngo, field, value)

    db.commit()
    db.refresh(ngo)
    return ngo

@router.put("/{ngo_id}/operating-hours", response_model=NGOResponse)
def update_ngo_operating_hours(
    ngo_id: int,
    hours_in: NGOOperatingHoursUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found.")

    if current_user.role != "admin" and ngo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update operating hours.")

    if isinstance(hours_in.operating_hours, str):
        ngo.operating_hours = hours_in.operating_hours
    else:
        ngo.operating_hours = json.dumps(hours_in.operating_hours)

    db.commit()
    db.refresh(ngo)
    return ngo

@router.put("/{ngo_id}/demands", response_model=NGOResponse)
def update_ngo_demands(
    ngo_id: int,
    demands_in: NGODemandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found.")

    if current_user.role != "admin" and ngo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update beneficiary demands.")

    if isinstance(demands_in.demand_requirements, str):
        ngo.demand_requirements = demands_in.demand_requirements
    else:
        ngo.demand_requirements = json.dumps(demands_in.demand_requirements)

    db.commit()
    db.refresh(ngo)
    return ngo

@router.post("/{ngo_id}/verify", response_model=NGOResponse)
def verify_ngo(
    ngo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found.")

    ngo.is_verified = True
    db.commit()
    db.refresh(ngo)
    return ngo

