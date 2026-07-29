from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.donation import FoodDonation
from app.models.donation_history import DonationHistory
from app.models.user import User
from app.schemas.donation import DonationCreate, DonationOut, DonationStatusUpdate, DonationUpdate

router = APIRouter(prefix="/donations", tags=["donations"])


@router.post("", response_model=DonationOut)
def create_donation(
    donation_in: DonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DonationOut:
    donation = FoodDonation(**donation_in.model_dump(), donor_id=current_user.id)
    db.add(donation)
    db.commit()
    db.refresh(donation)
    history = DonationHistory(donation_id=donation.id, action="created", performed_by=current_user.id)
    db.add(history)
    db.commit()
    return donation


@router.get("", response_model=list[DonationOut])
def list_donations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[DonationOut]:
    donations = db.query(FoodDonation).filter(FoodDonation.donor_id == current_user.id).all()
    return donations


@router.get("/available", response_model=list[DonationOut])
def list_available_donations(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[DonationOut]:
    if current_user.role != "ngo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NGO access required")
    return db.query(FoodDonation).filter(FoodDonation.status.in_(["pending", "accepted"])).all()


@router.patch("/{donation_id}/status", response_model=DonationOut)
def update_donation_status(
    donation_id: int,
    status_in: DonationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DonationOut:
    if current_user.role != "ngo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NGO access required")
    if status_in.status not in {"accepted", "completed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid donation status")

    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if donation.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Donation is already completed")

    donation.status = status_in.status
    db.add(DonationHistory(donation_id=donation.id, action=status_in.status, performed_by=current_user.id))
    db.commit()
    db.refresh(donation)
    return donation


@router.get("/{donation_id}", response_model=DonationOut)
def get_donation(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> DonationOut:
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id, FoodDonation.donor_id == current_user.id).first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    return donation


@router.put("/{donation_id}", response_model=DonationOut)
def update_donation(
    donation_id: int,
    donation_in: DonationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DonationOut:
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id, FoodDonation.donor_id == current_user.id).first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    for key, value in donation_in.model_dump().items():
        setattr(donation, key, value)
    db.commit()
    db.refresh(donation)
    return donation


@router.delete("/{donation_id}")
def delete_donation(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, str]:
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id, FoodDonation.donor_id == current_user.id).first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    db.delete(donation)
    db.commit()
    return {"message": "Donation deleted"}
