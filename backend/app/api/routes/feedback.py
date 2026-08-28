from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.models import (
    FoodDonation, User, NGO, RescueFeedback, RescueIssueReport, VolunteerAssignment
)
from app.schemas.schemas import (
    RescueFeedbackCreate, RescueFeedbackResponse,
    RescueIssueReportCreate, RescueIssueReportResponse, RescueIssueResolveRequest,
    ParticipantReliabilityResponse, AdminFeedbackOverviewResponse
)
from app.core.dependencies import get_current_user, require_role
from app.services.notification_service import create_notification
from app.services.security_service import log_audit_event
from app.services.reliability_service import get_participant_reliability

router = APIRouter(prefix="", tags=["Rescue Feedback & Trust"])


def _is_donation_participant(donation: FoodDonation, user: User, db: Session) -> bool:
    """Verifies whether a user was genuinely involved in the donation lifecycle."""
    if user.role == "admin":
        return True
    if donation.donor_id == user.id:
        return True
    if donation.assigned_volunteer_id == user.id:
        return True
    if donation.assigned_ngo_id:
        ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first()
        if ngo and ngo.user_id == user.id:
            return True
    return False


def _derive_issue_severity(category: str, is_food_safety: bool) -> str:
    if is_food_safety or category in ["food_condition_concern", "otp_issue"]:
        return "CRITICAL"
    if category in ["volunteer_no_show", "donor_unavailable", "ngo_unavailable", "quantity_mismatch"]:
        return "HIGH"
    if category in ["volunteer_late", "packaging_damaged", "delivery_issue", "distribution_issue"]:
        return "MEDIUM"
    return "LOW"


# ── Participant Rescue Feedback ──────────────────────────────────────────────

@router.post("/donations/{donation_id}/feedback", response_model=RescueFeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_rescue_feedback(
    donation_id: int,
    feedback_in: RescueFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits structured operational rescue feedback.
    Enforces that only genuine participants (Donor, assigned NGO, assigned Volunteer) can submit.
    Enforces one primary feedback submission per participant per rescue.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # 1. Access Control: Genuine participant check
    if not _is_donation_participant(donation, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only verified participants of this rescue can submit operational feedback."
        )

    # 2. Abuse Protection: Duplicate check
    existing = db.query(RescueFeedback).filter(
        RescueFeedback.donation_id == donation.id,
        RescueFeedback.author_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted feedback for this rescue."
        )

    # 3. Resolve target user and NGO based on author's role
    target_user_id = None
    target_ngo_id = donation.assigned_ngo_id

    if current_user.role == "donor":
        target_user_id = donation.assigned_volunteer_id
    elif current_user.role == "ngo":
        target_user_id = donation.assigned_volunteer_id or donation.donor_id
    elif current_user.role == "volunteer":
        target_user_id = donation.donor_id

    new_feedback = RescueFeedback(
        donation_id=donation.id,
        author_id=current_user.id,
        author_role=current_user.role,
        target_user_id=target_user_id,
        target_ngo_id=target_ngo_id,
        overall_rating=feedback_in.overall_rating,
        pickup_timeliness=feedback_in.pickup_timeliness,
        handover_experience=feedback_in.handover_experience,
        communication_quality=feedback_in.communication_quality,
        app_experience=feedback_in.app_experience,
        food_condition_rating=feedback_in.food_condition_rating,
        quantity_accuracy=feedback_in.quantity_accuracy,
        packaging_quality=feedback_in.packaging_quality,
        volunteer_punctuality=feedback_in.volunteer_punctuality,
        volunteer_professionalism=feedback_in.volunteer_professionalism,
        donor_readiness=feedback_in.donor_readiness,
        pickup_location_clarity=feedback_in.pickup_location_clarity,
        packaging_readiness=feedback_in.packaging_readiness,
        ngo_receiving_readiness=feedback_in.ngo_receiving_readiness,
        comment=feedback_in.comment,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    # Recalculate participant reliability in background/sync
    try:
        if target_user_id:
            get_participant_reliability(db, target_user_id)
        get_participant_reliability(db, current_user.id)
    except Exception:
        pass

    # Send confirmation notification to participant
    create_notification(
        db,
        user_id=current_user.id,
        title="Feedback Recorded",
        message=f"Thank you! Your feedback for rescue #{donation.id} has been recorded.",
        type="info",
        related_donation_id=donation.id
    )

    log_audit_event(
        db, action="rescue_feedback_submitted", user_id=current_user.id,
        resource_type="donation", resource_id=donation.id, status_code="success",
        details=f"Feedback #{new_feedback.id} ({feedback_in.overall_rating} stars) submitted by {current_user.role}"
    )

    res = RescueFeedbackResponse.model_validate(new_feedback)
    res.author_name = current_user.name
    return res


@router.get("/donations/{donation_id}/feedback", response_model=List[RescueFeedbackResponse])
def get_donation_feedbacks(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns submitted feedback for a donation.
    Accessible only to participating parties and platform administrators.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if not _is_donation_participant(donation, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view feedback for this donation."
        )

    feedbacks = db.query(RescueFeedback).filter(RescueFeedback.donation_id == donation_id).all()
    results = []
    for f in feedbacks:
        item = RescueFeedbackResponse.model_validate(f)
        author = db.query(User).filter(User.id == f.author_id).first()
        item.author_name = author.name if author else "Participant"
        results.append(item)
    return results


# ── Rescue Problem & Incident Reporting ──────────────────────────────────────

@router.post("/donations/{donation_id}/issues", response_model=RescueIssueReportResponse, status_code=status.HTTP_201_CREATED)
def report_rescue_issue(
    donation_id: int,
    issue_in: RescueIssueReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reports an operational problem or food-safety condition concern.
    Keeps food condition incident reports separate from normal service feedback.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if not _is_donation_participant(donation, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants involved in this rescue can report an operational issue."
        )

    severity = _derive_issue_severity(issue_in.category, issue_in.is_food_safety_incident)

    # Determine reported party
    reported_user_id = None
    reported_ngo_id = None
    if issue_in.category in ["volunteer_no_show", "volunteer_late"]:
        reported_user_id = donation.assigned_volunteer_id
    elif issue_in.category in ["donor_unavailable", "food_condition_concern"]:
        reported_user_id = donation.donor_id
    elif issue_in.category == "ngo_unavailable":
        reported_ngo_id = donation.assigned_ngo_id

    new_issue = RescueIssueReport(
        donation_id=donation.id,
        reporter_id=current_user.id,
        reporter_role=current_user.role,
        reported_user_id=reported_user_id,
        reported_ngo_id=reported_ngo_id,
        category=issue_in.category,
        severity=severity,
        is_food_safety_incident=issue_in.is_food_safety_incident or (issue_in.category == "food_condition_concern"),
        food_safety_details=issue_in.food_safety_details,
        description=issue_in.description,
        evidence_url=issue_in.evidence_url,
        status="OPEN",
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)

    # High / Critical severity alert to all admins
    if severity in ["HIGH", "CRITICAL"]:
        admins = db.query(User).filter(User.role == "admin").all()
        for admin in admins:
            create_notification(
                db,
                user_id=admin.id,
                title=f"New {severity} Rescue Issue Reported",
                message=f"Donation #{donation.id}: '{issue_in.category}' reported by {current_user.name} ({current_user.role}).",
                type="alert",
                related_donation_id=donation.id
            )

    log_audit_event(
        db, action="rescue_issue_reported", user_id=current_user.id,
        resource_type="donation", resource_id=donation.id, status_code="success",
        details=f"Issue #{new_issue.id} ({severity}) reported by {current_user.role}: {issue_in.category}"
    )

    res = RescueIssueReportResponse.model_validate(new_issue)
    res.reporter_name = current_user.name
    res.food_name = donation.food_name
    return res


@router.get("/donations/{donation_id}/issues", response_model=List[RescueIssueReportResponse])
def list_donation_issues(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists issues reported for a specific donation."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if not _is_donation_participant(donation, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view issues for this donation."
        )

    issues = db.query(RescueIssueReport).filter(RescueIssueReport.donation_id == donation_id).all()
    results = []
    for issue in issues:
        item = RescueIssueReportResponse.model_validate(issue)
        reporter = db.query(User).filter(User.id == issue.reporter_id).first()
        item.reporter_name = reporter.name if reporter else "Reporter"
        item.food_name = donation.food_name
        results.append(item)
    return results


# ── Personal Feedback History & Reliability ──────────────────────────────────

@router.get("/feedback/my", response_model=List[RescueFeedbackResponse])
def get_my_feedback_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns feedback submitted by the authenticated user."""
    feedbacks = db.query(RescueFeedback).filter(
        RescueFeedback.author_id == current_user.id
    ).order_by(RescueFeedback.created_at.desc()).all()

    results = []
    for f in feedbacks:
        item = RescueFeedbackResponse.model_validate(f)
        item.author_name = current_user.name
        results.append(item)
    return results


@router.get("/users/{user_id}/reliability", response_model=ParticipantReliabilityResponse)
def get_user_reliability_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns explainable participant reliability metrics."""
    return get_participant_reliability(db, user_id)


# ── Admin Feedback & Issues Dashboard Endpoints ──────────────────────────────

@router.get("/admin/feedback/overview", response_model=AdminFeedbackOverviewResponse)
def get_admin_feedback_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Provides high-level triage analytics for operational feedback and issues."""
    total_feedbacks = db.query(RescueFeedback).count()
    avg_rating = db.query(func.avg(RescueFeedback.overall_rating)).scalar() or 5.0

    open_issues = db.query(RescueIssueReport).filter(RescueIssueReport.status == "OPEN").count()
    critical_issues = db.query(RescueIssueReport).filter(
        RescueIssueReport.status == "OPEN",
        RescueIssueReport.severity == "CRITICAL"
    ).count()
    high_issues = db.query(RescueIssueReport).filter(
        RescueIssueReport.status == "OPEN",
        RescueIssueReport.severity == "HIGH"
    ).count()

    # Alerts based on active issues
    vol_alerts = db.query(RescueIssueReport).filter(
        RescueIssueReport.status == "OPEN",
        RescueIssueReport.category.in_(["volunteer_no_show", "volunteer_late"])
    ).count()

    ngo_alerts = db.query(RescueIssueReport).filter(
        RescueIssueReport.status == "OPEN",
        RescueIssueReport.category.in_(["ngo_unavailable", "quantity_mismatch"])
    ).count()

    donor_alerts = db.query(RescueIssueReport).filter(
        RescueIssueReport.status == "OPEN",
        RescueIssueReport.category.in_(["donor_unavailable", "food_condition_concern"])
    ).count()

    recent_issues_raw = db.query(RescueIssueReport).order_by(RescueIssueReport.created_at.desc()).limit(10).all()
    recent_issues = []
    for issue in recent_issues_raw:
        item = RescueIssueReportResponse.model_validate(issue)
        rep = db.query(User).filter(User.id == issue.reporter_id).first()
        item.reporter_name = rep.name if rep else "Reporter"
        don = db.query(FoodDonation).filter(FoodDonation.id == issue.donation_id).first()
        if don:
            item.food_name = don.food_name
        recent_issues.append(item)

    return AdminFeedbackOverviewResponse(
        total_feedback_count=total_feedbacks,
        average_experience_rating=round(float(avg_rating), 2),
        open_issues_count=open_issues,
        critical_issues_count=critical_issues,
        high_severity_count=high_issues,
        volunteer_reliability_alerts_count=vol_alerts,
        ngo_reliability_alerts_count=ngo_alerts,
        donor_readiness_alerts_count=donor_alerts,
        recent_issues=recent_issues
    )


@router.get("/admin/feedback", response_model=List[RescueFeedbackResponse])
def list_admin_feedbacks(
    role_filter: Optional[str] = Query(None, alias="role"),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Admin endpoint to inspect all rescue feedback with pagination and filters."""
    query = db.query(RescueFeedback)
    if role_filter:
        query = query.filter(RescueFeedback.author_role == role_filter)
    if min_rating:
        query = query.filter(RescueFeedback.overall_rating >= min_rating)

    feedbacks = query.order_by(RescueFeedback.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    for f in feedbacks:
        item = RescueFeedbackResponse.model_validate(f)
        author = db.query(User).filter(User.id == f.author_id).first()
        item.author_name = author.name if author else "Participant"
        results.append(item)
    return results


@router.get("/admin/issues", response_model=List[RescueIssueReportResponse])
def list_admin_issues(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    category_filter: Optional[str] = Query(None, alias="category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Admin endpoint to triage and inspect reported rescue issues."""
    query = db.query(RescueIssueReport)
    if status_filter:
        query = query.filter(RescueIssueReport.status == status_filter.upper())
    if severity_filter:
        query = query.filter(RescueIssueReport.severity == severity_filter.upper())
    if category_filter:
        query = query.filter(RescueIssueReport.category == category_filter)

    issues = query.order_by(RescueIssueReport.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    for issue in issues:
        item = RescueIssueReportResponse.model_validate(issue)
        rep = db.query(User).filter(User.id == issue.reporter_id).first()
        item.reporter_name = rep.name if rep else "Reporter"
        don = db.query(FoodDonation).filter(FoodDonation.id == issue.donation_id).first()
        if don:
            item.food_name = don.food_name
        if issue.reported_user_id:
            reported_u = db.query(User).filter(User.id == issue.reported_user_id).first()
            if reported_u:
                item.reported_user_name = reported_u.name
        if issue.reported_ngo_id:
            reported_n = db.query(NGO).filter(NGO.id == issue.reported_ngo_id).first()
            if reported_n:
                item.reported_ngo_name = reported_n.organization_name

        # Count previous issues reported on this same participant
        if issue.reported_user_id:
            item.reporter_history_count = db.query(RescueIssueReport).filter(
                RescueIssueReport.reported_user_id == issue.reported_user_id
            ).count()
        results.append(item)
    return results


@router.get("/admin/issues/{issue_id}", response_model=RescueIssueReportResponse)
def get_admin_issue_detail(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Gets detailed record of a reported rescue issue."""
    issue = db.query(RescueIssueReport).filter(RescueIssueReport.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue report not found.")

    item = RescueIssueReportResponse.model_validate(issue)
    rep = db.query(User).filter(User.id == issue.reporter_id).first()
    item.reporter_name = rep.name if rep else "Reporter"
    don = db.query(FoodDonation).filter(FoodDonation.id == issue.donation_id).first()
    if don:
        item.food_name = don.food_name
    if issue.resolved_by:
        resolver = db.query(User).filter(User.id == issue.resolved_by).first()
        if resolver:
            item.resolver_name = resolver.name

    if issue.reported_user_id:
        item.reporter_history_count = db.query(RescueIssueReport).filter(
            RescueIssueReport.reported_user_id == issue.reported_user_id
        ).count()

    return item


@router.post("/admin/issues/{issue_id}/resolve", response_model=RescueIssueReportResponse)
def resolve_admin_issue(
    issue_id: int,
    resolve_in: RescueIssueResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Admin action to resolve or dismiss an issue with audit trail and optional trust adjustment.
    """
    issue = db.query(RescueIssueReport).filter(RescueIssueReport.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue report not found.")

    status_val = resolve_in.status.upper()
    if status_val not in ["RESOLVED", "DISMISSED", "UNDER_REVIEW", "ACTION_REQUIRED"]:
        status_val = "RESOLVED"

    issue.status = status_val
    issue.admin_notes = resolve_in.admin_notes
    issue.resolved_by = current_user.id
    issue.resolved_at = datetime.now(timezone.utc)

    # Apply penalty if specified and issue is validated
    if resolve_in.reliability_penalty and resolve_in.reliability_penalty > 0 and status_val == "RESOLVED":
        if issue.reported_user_id:
            rep_user = db.query(User).filter(User.id == issue.reported_user_id).first()
            if rep_user:
                if rep_user.role == "volunteer":
                    rep_user.reliability_score = max(50.0, (rep_user.reliability_score or 95.0) - resolve_in.reliability_penalty)
                elif rep_user.role == "donor":
                    rep_user.donor_trust_score = max(50.0, (rep_user.donor_trust_score or 98.0) - resolve_in.reliability_penalty)
        elif issue.reported_ngo_id:
            rep_ngo = db.query(NGO).filter(NGO.id == issue.reported_ngo_id).first()
            if rep_ngo:
                rep_ngo.trust_score = max(50.0, (rep_ngo.trust_score or 96.0) - resolve_in.reliability_penalty)

    # Notify reporter
    create_notification(
        db,
        user_id=issue.reporter_id,
        title=f"Rescue Issue {status_val.capitalize()}",
        message=f"Your report on donation #{issue.donation_id} has been reviewed and marked '{status_val}'.",
        type="info",
        related_donation_id=issue.donation_id
    )

    db.commit()
    db.refresh(issue)

    log_audit_event(
        db, action="rescue_issue_resolved", user_id=current_user.id,
        resource_type="rescue_issue_report", resource_id=issue.id, status_code="success",
        details=f"Issue #{issue.id} marked {status_val} by Admin {current_user.id} (Penalty: {resolve_in.reliability_penalty or 0.0})"
    )

    item = RescueIssueReportResponse.model_validate(issue)
    item.resolver_name = current_user.name
    return item


@router.post("/admin/issues/{issue_id}/dismiss", response_model=RescueIssueReportResponse)
def dismiss_admin_issue(
    issue_id: int,
    dismiss_in: Optional[RescueIssueResolveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Marks a report as dismissed (e.g. false alarm or invalid report)."""
    notes = dismiss_in.admin_notes if dismiss_in else "Dismissed after admin review."
    req = RescueIssueResolveRequest(status="DISMISSED", admin_notes=notes, reliability_penalty=0.0)
    return resolve_admin_issue(issue_id, req, db, current_user)
