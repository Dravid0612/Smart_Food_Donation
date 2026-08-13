from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.models import NGO, User
from app.schemas.schemas import NGOResponse, NGOUpdate
from app.core.dependencies import get_current_user, require_role

router = APIRouter(prefix="/ngos", tags=["NGOs"])

@router.get("", response_model=List[NGOResponse])
def get_ngos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ngos = db.query(NGO).all()
    return ngos

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
