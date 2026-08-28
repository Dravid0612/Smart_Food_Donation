from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Core authentication dependency ───────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Validates JWT, loads user from DB, checks account is active.
    This is the PRIMARY security boundary — every protected endpoint must use this.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Always re-fetch from DB — never trust cached token state for active status
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        # HTTP 403 Forbidden — account deactivated by admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact the platform administrator."
        )
    return user

# ── Role-based access control ─────────────────────────────────────────────────

def require_role(allowed_roles: list[str]):
    """Enforces role-based access. Requires authenticated + active user."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized for this endpoint."
            )
        return current_user
    return role_checker

# ── NGO verification dependency ───────────────────────────────────────────────

def require_verified_ngo(
    current_user: User = Depends(require_role(["ngo"])),
    db: Session = Depends(get_db)
) -> User:
    """
    Enforces: authenticated + active + role=ngo + NGO profile is VERIFIED.
    Being an NGO user is NOT sufficient — the NGO must be admin-approved.
    """
    ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
    if not ngo_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NGO profile not found for this account."
        )
    if not ngo_profile.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NGO account is not yet verified. Please contact the administrator for approval."
        )
    return current_user

# ── Resource ownership dependencies ──────────────────────────────────────────

def require_donation_owner(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> FoodDonation:
    """
    Loads a donation and enforces that current_user is the donor (or admin).
    Returns the donation if authorized, raises 404 (enumeration protection) if not the owner.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found.")
    if current_user.role != "admin" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this donation.")
    return donation

def require_assignment_owner(assignment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> VolunteerAssignment:
    """
    Loads a volunteer assignment and enforces that current_user is the assigned volunteer (or admin).
    """
    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    if current_user.role != "admin" and assignment.volunteer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this assignment.")
    return assignment

def require_ngo_owner(ngo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> NGO:
    """
    Loads an NGO and enforces that current_user is its owner (or admin).
    """
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found.")
    if current_user.role != "admin" and ngo.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage this NGO.")
    return ngo
