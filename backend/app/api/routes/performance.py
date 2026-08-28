"""
Performance, Reliability Analytics & Matching Optimization REST Endpoints.
Provides personal performance transparency, network failure analytics, needs-review queue,
suspicious feedback detection, and administrative performance actions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import (
    PerformanceProfileResponse,
    AdminPerformanceOverviewResponse,
    RescueFailureAnalyticsResponse,
    NeedsReviewParticipantResponse,
    SuspiciousFeedbackAlertResponse,
    AdminPerformanceActionRequest,
    AdminPerformanceActionResponse,
)
from app.core.dependencies import get_current_user
from app.services.reliability_service import (
    get_participant_reliability,
    calculate_volunteer_reliability,
    calculate_ngo_reliability,
    calculate_donor_reliability,
    calculate_rescue_performance_overview,
    calculate_rescue_failure_analytics,
    get_needs_review_participants,
    detect_suspicious_feedback,
    execute_admin_performance_action,
)

router = APIRouter(prefix="", tags=["performance"])


@router.get("/users/me/performance", response_model=PerformanceProfileResponse)
def get_my_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns personal performance breakdown, raw metrics, derived rates,
    and constructive trend descriptions for the logged-in user.
    """
    profile = get_participant_reliability(db, current_user.id)
    return profile


@router.get("/users/{user_id}/performance", response_model=PerformanceProfileResponse)
def get_user_performance(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns operational performance profile for a specific user.
    Admins can view any participant; participants can view their own profile.
    """
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    profile = get_participant_reliability(db, user_id)
    return profile


@router.get("/admin/performance/overview", response_model=AdminPerformanceOverviewResponse)
def get_admin_performance_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aggregates network-wide operational KPIs:
    - Average pickup time, response time, volunteer acceptance rate
    - Network on-time rate, completion rate, rescue success rate
    - Fallback escalation rate, needs-review count, critical alerts count
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to view performance overview"
        )

    overview = calculate_rescue_performance_overview(db)
    return overview


@router.get("/admin/performance/failures", response_model=RescueFailureAnalyticsResponse)
def get_rescue_failure_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns failure reasons breakdown, counts, percentages, and trends.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to view failure analytics"
        )

    analytics = calculate_rescue_failure_analytics(db)
    return analytics


@router.get("/admin/performance/needs-review", response_model=List[NeedsReviewParticipantResponse])
def get_needs_review_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns list of participants flagged for administrative review due to
    elevated no-show rate, cancellation rate, or low intake readiness.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to view needs review queue"
        )

    items = get_needs_review_participants(db)
    return items


@router.get("/admin/performance/suspicious-feedback", response_model=List[SuspiciousFeedbackAlertResponse])
def get_suspicious_feedback_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns flagged feedback submissions (repetitive spam comments, rating bursts, retaliatory clusters)
    for human review without automatic algorithmic penalties.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to view suspicious feedback alerts"
        )

    alerts = detect_suspicious_feedback(db)
    return alerts


@router.post("/admin/users/{user_id}/performance-action", response_model=AdminPerformanceActionResponse)
def execute_performance_action(
    user_id: int,
    action_in: AdminPerformanceActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes administrative intervention action on a participant:
    MONITOR, CONTACT, TEMPORARILY_DEPRIORITIZE, REQUIRE_CONFIRMATION, DISABLE_AVAILABILITY, RESTORE.
    Records audit log and updates matching prioritization.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to perform administrative actions"
        )

    result = execute_admin_performance_action(
        db=db,
        admin_id=current_user.id,
        target_user_id=user_id,
        action=action_in.action,
        notes=action_in.notes,
        deprioritize_factor=action_in.deprioritize_factor or 0.7
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to execute performance action")
        )

    return result
