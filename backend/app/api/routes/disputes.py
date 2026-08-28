from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Dispute, FoodDonation, User, NGO
from app.schemas.schemas import DisputeCreateRequest, DisputeResolveRequest, DisputeResponse
from app.core.dependencies import get_current_user, require_role
from app.services.notification_service import create_notification
from app.services.security_service import log_audit_event

router = APIRouter(prefix="/disputes", tags=["Disputes & Issue Reporting"])

@router.post("", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
def report_dispute(
    dispute_in: DisputeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows any participating party (Donor, NGO, Volunteer) to report an operational dispute or issue.
    Issues: food_condition_mismatch, volunteer_no_show, donor_unavailable, ngo_unavailable, other.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == dispute_in.donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    new_dispute = Dispute(
        donation_id=donation.id,
        reporter_id=current_user.id,
        role=current_user.role,
        issue_type=dispute_in.issue_type,
        description=dispute_in.description,
        status="open",
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_dispute)
    db.commit()
    db.refresh(new_dispute)

    # Notify Admins of newly reported issue
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        create_notification(
            db,
            user_id=admin.id,
            title="New Issue Reported",
            message=f"Dispute reported on donation #{donation.id} by {current_user.name} ({current_user.role}): '{dispute_in.issue_type}'",
            type="alert",
            related_donation_id=donation.id
        )

    log_audit_event(
        db, action="dispute_reported", user_id=current_user.id,
        resource_type="donation", resource_id=donation.id, status_code="success",
        details=f"Dispute #{new_dispute.id} created: {dispute_in.issue_type}"
    )

    return new_dispute

@router.get("", response_model=List[DisputeResponse])
def list_disputes(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists disputes. Admin sees all system disputes; other users see disputes they reported.
    """
    query = db.query(Dispute)
    if current_user.role != "admin":
        query = query.filter(Dispute.reporter_id == current_user.id)
    if status_filter:
        query = query.filter(Dispute.status == status_filter)
    return query.order_by(Dispute.created_at.desc()).all()

@router.put("/{dispute_id}/resolve", response_model=DisputeResponse)
def resolve_dispute(
    dispute_id: int,
    resolve_in: DisputeResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Admin review & resolution for reported disputes, with optional trust score adjustments.
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found.")

    dispute.status = resolve_in.status
    dispute.admin_notes = resolve_in.admin_notes
    dispute.resolved_by = current_user.id
    dispute.trust_score_penalty = resolve_in.trust_score_penalty or 0.0
    dispute.resolved_at = datetime.now(timezone.utc)

    # If trust penalty specified, apply to target party
    if dispute.trust_score_penalty and dispute.trust_score_penalty > 0:
        donation = db.query(FoodDonation).filter(FoodDonation.id == dispute.donation_id).first()
        if donation:
            if dispute.issue_type in ["volunteer_no_show", "pickup_failed"] and donation.assigned_volunteer_id:
                vol = db.query(User).filter(User.id == donation.assigned_volunteer_id).first()
                if vol:
                    vol.reliability_score = max(50.0, (vol.reliability_score or 95.0) - dispute.trust_score_penalty)
            elif dispute.issue_type in ["food_condition_mismatch"] and donation.donor_id:
                donor = db.query(User).filter(User.id == donation.donor_id).first()
                if donor:
                    donor.donor_trust_score = max(50.0, (donor.donor_trust_score or 98.0) - dispute.trust_score_penalty)
            elif dispute.issue_type in ["ngo_unavailable"] and donation.assigned_ngo_id:
                ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first()
                if ngo:
                    ngo.trust_score = max(50.0, (ngo.trust_score or 96.0) - dispute.trust_score_penalty)

    # Notify reporter of resolution
    create_notification(
        db,
        user_id=dispute.reporter_id,
        title="Dispute Resolved",
        message=f"Your reported issue on donation #{dispute.donation_id} has been reviewed and marked '{dispute.status}'.",
        type="info",
        related_donation_id=dispute.donation_id
    )

    db.commit()
    db.refresh(dispute)

    log_audit_event(
        db, action="dispute_resolved", user_id=current_user.id,
        resource_type="dispute", resource_id=dispute.id, status_code="success",
        details=f"Dispute #{dispute.id} resolved as {dispute.status}"
    )

    return dispute
