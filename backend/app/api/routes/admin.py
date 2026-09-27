from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, String
from typing import List, Optional
from app.db.session import get_db
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment, RescueIssueReport, AuditLog, DonationHistory
from app.schemas.schemas import (
    AdminStatsResponse, UserResponse, NGOResponse, DonationResponse,
    AdminInterventionItem, AdminInterventionsResponse,
    AdminReceivingSummaryResponse, AdminReceivingItemResponse, AdminReceivingListResponse,
    AdminRescueDetailResponse, AdminRescueAuditTimelineItem,
    AdminInterventionCreate, AdminInterventionActionResponse,
    NGOCapacityItemResponse, AdminCategoryBreakdownResponse, AdminCategoryBreakdownItem,
    RescueIssueReportResponse
)
from app.core.dependencies import require_role
from app.services.urgency_service import calculate_urgency
from app.services.security_service import log_audit_event
from app.services.state_machine_service import transition_donation_status, transition_donation_state
from app.services.notification_service import create_event_notification

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
        FoodDonation.status.in_(["delivered", "completed", "partially_distributed"])
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

    action = "account_activated" if user.is_active else "account_deactivated"
    log_audit_event(
        db, action=action,
        user_id=current_user.id,
        resource_type="user",
        resource_id=user.id,
        status_code="success",
        details=f"Admin {current_user.id} set user {user.id} ({user.role}) is_active={user.is_active}"
    )
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

# ── 1. RECEIVING & OPERATIONS OVERVIEW SUMMARY ───────────────────────────────

@router.get("/receiving/summary", response_model=AdminReceivingSummaryResponse)
@router.get("/rescue-overview", response_model=AdminReceivingSummaryResponse)
def get_admin_receiving_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Computes real-time operational metrics across all active and completed rescues.
    All figures are aggregated directly from the database state.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active rescues (currently in progress or awaiting action)
    active_statuses = ["pending", "accepted", "volunteer_assigned", "collected", "delivered", "partially_distributed"]
    active_donations = db.query(FoodDonation).filter(FoodDonation.status.in_(active_statuses)).all()
    active_rescues = len(active_donations)

    urgent_rescues = 0
    critical_rescues = 0
    food_at_risk_meals = 0.0

    for d in active_donations:
        urgency = (d.rescue_urgency_level or "").upper()
        rem_min = d.remaining_minutes
        if rem_min is None and d.expiry_time:
            exp = d.expiry_time if d.expiry_time.tzinfo else d.expiry_time.replace(tzinfo=timezone.utc)
            rem_min = max(0, int((exp - now).total_seconds() / 60))

        if urgency == "CRITICAL" or (rem_min is not None and rem_min <= 30) or d.status in ["pickup_failed", "delivery_failed"]:
            critical_rescues += 1
            food_at_risk_meals += float(d.quantity)
        elif urgency == "URGENT" or (rem_min is not None and rem_min <= 90) or d.is_emergency:
            urgent_rescues += 1
            food_at_risk_meals += float(d.quantity)

    # Food in transit
    in_transit = db.query(FoodDonation).filter(FoodDonation.status == "collected").count()

    # Food received today
    received_today = db.query(func.sum(
        func.coalesce(FoodDonation.received_quantity, FoodDonation.quantity)
    )).filter(
        FoodDonation.status.in_(["delivered", "partially_distributed", "completed"])
    ).scalar() or 0.0

    # Food distributed today
    distributed_today = db.query(func.sum(
        func.coalesce(FoodDonation.distributed_quantity, FoodDonation.beneficiaries_served, 0.0)
    )).filter(
        FoodDonation.status.in_(["partially_distributed", "completed"])
    ).scalar() or 0.0

    # Remaining food currently held awaiting distribution
    remaining_today = db.query(func.sum(
        func.coalesce(FoodDonation.remaining_quantity, 0.0)
    )).filter(
        FoodDonation.status.in_(["delivered", "partially_distributed"])
    ).scalar() or 0.0

    # Open issues requiring action
    issues_open = db.query(RescueIssueReport).filter(
        RescueIssueReport.status.in_(["OPEN", "UNDER_REVIEW", "ACTION_REQUIRED"])
    ).count()

    # Completed rescues
    completed_today = db.query(FoodDonation).filter(
        FoodDonation.status == "completed"
    ).count()

    return AdminReceivingSummaryResponse(
        active_rescues=active_rescues,
        urgent_rescues=urgent_rescues,
        critical_rescues=critical_rescues,
        in_transit=in_transit,
        received_today=float(received_today),
        distributed_today=float(distributed_today),
        remaining_today=float(remaining_today),
        issues_open=issues_open,
        food_at_risk_meals=float(food_at_risk_meals),
        completed_today=completed_today
    )

# ── 2. RECEIVING OPERATIONAL QUEUE (FILTERED & PAGINATED) ───────────────────

def _format_receiving_item(d: FoodDonation, db: Session) -> AdminReceivingItemResponse:
    now = datetime.now(timezone.utc)
    donor = d.donor
    ngo = d.assigned_ngo
    volunteer = d.assigned_volunteer

    donor_name = donor.name if donor else "Anonymous Donor"
    donor_phone = donor.phone if donor else None
    ngo_name = ngo.organization_name if ngo else None
    volunteer_name = volunteer.name if volunteer else None
    volunteer_phone = volunteer.phone if volunteer else None

    # Calculate remaining minutes dynamically if needed
    rem_min = d.remaining_minutes
    if rem_min is None and d.expiry_time:
        exp = d.expiry_time if d.expiry_time.tzinfo else d.expiry_time.replace(tzinfo=timezone.utc)
        rem_min = max(0, int((exp - now).total_seconds() / 60))

    urgency = d.rescue_urgency_level or "FRESH"
    if rem_min is not None:
        if rem_min <= 0:
            urgency = "RESCUE_WINDOW_ENDED"
        elif rem_min <= 30 or d.status in ["pickup_failed", "delivery_failed"]:
            urgency = "CRITICAL"
        elif rem_min <= 90 or d.is_emergency:
            urgency = "URGENT"
        elif rem_min <= 180:
            urgency = "APPROACHING"

    # ETA estimation (based on live tracking or volunteer state)
    eta_min = d.current_eta_minutes
    if eta_min is None:
        if d.status in ["collected", "in_transit"]:
            eta_min = 12.0
        elif d.status in ["volunteer_assigned", "en_route", "pickup_en_route"]:
            eta_min = 25.0

    # Quantity mismatch analysis
    expected_qty = float(d.quantity)
    received_qty = float(d.received_quantity) if d.received_quantity is not None else None
    has_mismatch = False
    discrepancy_amount = None
    discrepancy_reason = None

    if received_qty is not None and abs(received_qty - expected_qty) > 0.01:
        has_mismatch = True
        discrepancy_amount = round(abs(expected_qty - received_qty), 2)
        discrepancy_reason = d.failure_reason or d.distribution_remarks or "Discrepancy noted on intake arrival"

    # Open issues for this donation
    issue_count = len(d.issue_reports) if d.issue_reports else 0

    return AdminReceivingItemResponse(
        id=d.id,
        food_name=d.food_name,
        food_category=d.food_category or "Cooked Food",
        quantity=float(d.quantity),
        quantity_unit=d.quantity_unit or "Meals",
        donor_id=d.donor_id,
        donor_name=donor_name,
        donor_phone=donor_phone,
        assigned_ngo_id=d.assigned_ngo_id,
        ngo_name=ngo_name,
        assigned_volunteer_id=d.assigned_volunteer_id,
        volunteer_name=volunteer_name,
        volunteer_phone=volunteer_phone,
        status=d.status,
        rescue_urgency_level=urgency,
        remaining_minutes=rem_min,
        ai_visual_condition=d.ai_visual_condition or "GOOD",
        storage_method=d.storage_method or "Room Temperature",
        packaging_condition=d.packaging_condition or "Sealed / Covered",
        eta_minutes=eta_min,
        expected_quantity=expected_qty,
        received_quantity=received_qty,
        has_quantity_mismatch=has_mismatch,
        discrepancy_amount=discrepancy_amount,
        discrepancy_reason=discrepancy_reason,
        distributed_quantity=float(d.distributed_quantity) if d.distributed_quantity is not None else None,
        remaining_quantity=float(d.remaining_quantity) if d.remaining_quantity is not None else None,
        issue_count=issue_count,
        pickup_address=d.pickup_address,
        created_at=d.created_at or now,
        accepted_at=d.created_at,
        collected_at=d.distribution_timestamp if d.status in ["delivered", "completed"] else None,
        delivered_at=d.distribution_timestamp if d.status in ["delivered", "completed"] else None,
        completed_at=d.distribution_timestamp if d.status == "completed" else None
    )

@router.get("/receiving", response_model=AdminReceivingListResponse)
@router.get("/rescues", response_model=AdminReceivingListResponse)
def get_admin_receiving_records(
    tab: str = Query("ALL", description="ALL, EXPECTED, ARRIVING, RECEIVED, DISTRIBUTING, COMPLETED, ISSUES, REMATCHED, LIVE_ACTIVE"),
    search: Optional[str] = Query(None, description="Search by ID, Food, Donor, NGO, Volunteer"),
    category: Optional[str] = Query(None, description="Filter by food category"),
    urgency: Optional[str] = Query(None, description="Filter by urgency level"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns the operations queue for food receiving, sorted by criticality and remaining time.
    """
    tab_upper = tab.upper().strip()
    query = db.query(FoodDonation)

    # 1. Apply Tab Filter
    if tab_upper == "EXPECTED":
        query = query.filter(FoodDonation.status.in_(["accepted", "volunteer_assigned"]))
    elif tab_upper == "ARRIVING":
        query = query.filter(FoodDonation.status.in_(["collected", "in_transit", "arrived_at_donor"]))
    elif tab_upper == "RECEIVED":
        query = query.filter(FoodDonation.status == "delivered")
    elif tab_upper == "DISTRIBUTING":
        query = query.filter(FoodDonation.status == "partially_distributed")
    elif tab_upper == "COMPLETED":
        query = query.filter(FoodDonation.status == "completed")
    elif tab_upper == "REMATCHED":
        query = query.filter(or_(FoodDonation.is_rematched == True, FoodDonation.rematch_count > 0))
    elif tab_upper == "LIVE_ACTIVE":
        query = query.filter(FoodDonation.status.in_(["accepted", "volunteer_assigned", "en_route", "pickup_en_route", "arrived_at_donor", "collected", "in_transit"]))
    elif tab_upper == "ISSUES":
        query = query.filter(
            or_(
                FoodDonation.status.in_(["pickup_failed", "delivery_failed", "cancelled"]),
                FoodDonation.feasibility_status.in_(["AT_RISK", "RESCUE_UNLIKELY"]),
                FoodDonation.id.in_(db.query(RescueIssueReport.donation_id).filter(RescueIssueReport.status != "RESOLVED"))
            )
        )

    # 2. Apply Category Filter
    if category and category.upper() != "ALL":
        query = query.filter(FoodDonation.food_category.ilike(f"%{category}%"))

    # 3. Apply Search Filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.join(FoodDonation.donor, isouter=True).join(FoodDonation.assigned_ngo, isouter=True).filter(
            or_(
                FoodDonation.food_name.ilike(term),
                FoodDonation.pickup_address.ilike(term),
                User.name.ilike(term),
                NGO.organization_name.ilike(term),
                func.cast(FoodDonation.id, String).ilike(term)
            )
        )

    all_donations = query.all()

    # 4. Multi-factor Sort:
    # 1. Urgency / Criticality (CRITICAL=1, URGENT=2, APPROACHING=3, FRESH=4, ENDED=5, COMPLETED=6)
    # 2. Remaining minutes (ascending)
    # 3. Created date (descending)
    def _urgency_weight(d: FoodDonation) -> tuple:
        status_val = (d.status or "").lower()
        if status_val in ["pickup_failed", "delivery_failed"]:
            return (0, 0, -(d.created_at.timestamp() if d.created_at else 0))

        urg = (d.rescue_urgency_level or "FRESH").upper()
        rem = d.remaining_minutes if d.remaining_minutes is not None else 99999

        score_map = {"CRITICAL": 1, "URGENT": 2, "APPROACHING": 3, "FRESH": 4, "RESCUE_WINDOW_ENDED": 5}
        urg_score = score_map.get(urg, 6)
        if status_val == "completed":
            urg_score = 10

        return (urg_score, rem, -(d.created_at.timestamp() if d.created_at else 0))

    sorted_donations = sorted(all_donations, key=_urgency_weight)

    # 5. Apply Urgency Filter after sorting if explicitly requested
    if urgency and urgency.upper() != "ALL":
        sorted_donations = [d for d in sorted_donations if (d.rescue_urgency_level or "").upper() == urgency.upper()]

    total_count = len(sorted_donations)
    start_idx = (page - 1) * page_size
    paged_donations = sorted_donations[start_idx : start_idx + page_size]

    items = [_format_receiving_item(d, db) for d in paged_donations]

    return AdminReceivingListResponse(
        total=total_count,
        page=page,
        page_size=page_size,
        items=items
    )

# ── 3. DETAILED FOOD RESCUE & AUDIT TIMELINE ─────────────────────────────────

@router.get("/rescues/{donation_id}", response_model=AdminRescueDetailResponse)
def get_admin_rescue_detail(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns full operational details, discrepancy audit, NGO capacity, and the 9-stage food flow stepper.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail=f"Donation #{donation_id} not found.")

    base_item = _format_receiving_item(donation, db)

    # Build 9-Stage Linear Stepper Timeline
    now = datetime.now(timezone.utc)
    status_lower = (donation.status or "").lower()

    # Stage flags
    stage_created = True
    stage_ai = bool(donation.food_analysis or donation.ai_visual_condition)
    stage_ngo = donation.assigned_ngo_id is not None
    stage_vol = donation.assigned_volunteer_id is not None
    stage_pickup = status_lower in ["collected", "delivered", "partially_distributed", "completed"]
    stage_transit = status_lower in ["collected", "delivered", "partially_distributed", "completed"]
    stage_received = status_lower in ["delivered", "partially_distributed", "completed"]
    stage_distribution = status_lower in ["partially_distributed", "completed"]
    stage_completed = status_lower == "completed"

    timeline = [
        AdminRescueAuditTimelineItem(
            stage="DONATION_CREATED",
            label="Donation Created",
            timestamp=donation.created_at,
            is_completed=stage_created,
            is_current=(status_lower == "pending" and not stage_ngo),
            actor_name=base_item.donor_name,
            details=f"Created {donation.quantity} {donation.quantity_unit} of {donation.food_name}"
        ),
        AdminRescueAuditTimelineItem(
            stage="AI_ANALYZED",
            label="AI Assessment & Rescue Window",
            timestamp=donation.created_at,
            is_completed=stage_ai,
            is_current=False,
            actor_name="AI Vision Engine",
            details=f"Visual condition: {donation.ai_visual_condition or 'GOOD'}, Window: {donation.remaining_minutes or 120} min"
        ),
        AdminRescueAuditTimelineItem(
            stage="NGO_ACCEPTED",
            label="Partner NGO Accepted",
            timestamp=donation.created_at,
            is_completed=stage_ngo,
            is_current=(status_lower == "accepted" and not stage_vol),
            actor_name=base_item.ngo_name or "Awaiting Partner NGO",
            details=f"Capacity reserved at {base_item.ngo_name or 'NGO Facility'}"
        ),
        AdminRescueAuditTimelineItem(
            stage="VOLUNTEER_ASSIGNED",
            label="Volunteer Courier Assigned",
            timestamp=donation.created_at,
            is_completed=stage_vol,
            is_current=(status_lower == "volunteer_assigned"),
            actor_name=base_item.volunteer_name or "Awaiting Courier Dispatch",
            details=f"Assigned courier: {base_item.volunteer_name or 'Pending'}"
        ),
        AdminRescueAuditTimelineItem(
            stage="PICKUP_VERIFIED",
            label="Handover & Secure OTP Verified",
            timestamp=base_item.collected_at,
            is_completed=stage_pickup,
            is_current=(status_lower == "collected"),
            actor_name=base_item.volunteer_name,
            details="Timing-safe cryptographic OTP verification completed at donor premises"
        ),
        AdminRescueAuditTimelineItem(
            stage="IN_TRANSIT",
            label="Food in Transit to NGO Facility",
            timestamp=base_item.collected_at,
            is_completed=stage_transit,
            is_current=(status_lower == "collected"),
            actor_name=base_item.volunteer_name,
            details="Transporting surplus food under insulated storage"
        ),
        AdminRescueAuditTimelineItem(
            stage="FOOD_RECEIVED",
            label="Food Intake & Condition Confirmed",
            timestamp=base_item.delivered_at,
            is_completed=stage_received,
            is_current=(status_lower == "delivered"),
            actor_name=base_item.ngo_name,
            details=f"Received {base_item.received_quantity or donation.quantity} meals at intake center"
        ),
        AdminRescueAuditTimelineItem(
            stage="BENEFICIARY_DISTRIBUTION",
            label="Beneficiary Meal Distribution",
            timestamp=donation.distribution_timestamp,
            is_completed=stage_distribution,
            is_current=(status_lower == "partially_distributed"),
            actor_name=base_item.ngo_name,
            details=f"Distributed {donation.distributed_quantity or 0} meals to community members"
        ),
        AdminRescueAuditTimelineItem(
            stage="RESCUE_COMPLETED",
            label="Rescue Completed & Impact Verified",
            timestamp=donation.distribution_timestamp if stage_completed else None,
            is_completed=stage_completed,
            is_current=stage_completed,
            actor_name="System",
            details="Waste averted, impact recorded, trust scores updated"
        )
    ]

    # NGO capacity info
    ngo_avail = True
    ngo_cur = None
    ngo_max = None
    if donation.assigned_ngo:
        ngo_cur = float(donation.assigned_ngo.current_capacity or 0.0)
        ngo_max = float(donation.assigned_ngo.capacity or 500.0)
        ngo_avail = (ngo_max - ngo_cur) >= float(donation.quantity)

    # Issue reports
    issues_resp = [
        RescueIssueReportResponse.model_validate(issue)
        for issue in donation.issue_reports
    ]

    return AdminRescueDetailResponse(
        **base_item.model_dump(),
        timeline=timeline,
        ngo_capacity_available=ngo_avail,
        ngo_current_capacity=ngo_cur,
        ngo_max_capacity=ngo_max,
        recent_issues=issues_resp
    )

# ── 4. ADMIN INTERVENTIONS WITH REASON & AUDIT TRAIL ─────────────────────────

@router.post("/interventions", response_model=AdminInterventionActionResponse)
def submit_admin_intervention(
    payload: AdminInterventionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Submits an administrative intervention for a donation with a mandatory reason code and audit logging.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == payload.donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail=f"Donation #{payload.donation_id} not found.")

    valid_reasons = [
        "no_volunteer_available", "ngo_unavailable", "pickup_delayed",
        "delivery_delayed", "food_condition_concern", "quantity_mismatch",
        "transport_failure", "other"
    ]
    if payload.reason_code not in valid_reasons:
        raise HTTPException(status_code=400, detail=f"Invalid reason_code. Must be one of: {', '.join(valid_reasons)}")

    # Mark as emergency if critical issue or transport failure
    if payload.reason_code in ["no_volunteer_available", "transport_failure", "pickup_delayed", "food_condition_concern"]:
        donation.is_emergency = True
        donation.escalated_at = datetime.now(timezone.utc)

    if payload.target_status:
        transition_donation_status(
            db=db,
            donation=donation,
            target_status=payload.target_status,
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Admin intervention ({payload.reason_code}): {payload.notes or ''}".strip(),
            force=True,
        )

    db.commit()

    # Log to audit trail
    audit_entry = log_audit_event(
        db,
        action="admin_rescue_intervention",
        user_id=current_user.id,
        resource_type="donation",
        resource_id=donation.id,
        status_code="success",
        details=f"Intervention Reason: {payload.reason_code}. Notes: {payload.notes or 'None'}. Action: {payload.action_type}"
    )

    # Emit canonical ADMIN_INTERVENTION event notifications
    create_event_notification(
        db=db,
        user_id=donation.donor_id,
        event_type="ADMIN_INTERVENTION",
        donation_id=donation.id,
        extra_message=f"Admin intervention applied: {payload.reason_code.replace('_', ' ').title()}."
    )
    if donation.assigned_volunteer_id:
        create_event_notification(
            db=db,
            user_id=donation.assigned_volunteer_id,
            event_type="ADMIN_INTERVENTION",
            donation_id=donation.id,
            extra_message=f"Admin intervention applied: {payload.reason_code.replace('_', ' ').title()}."
        )
    if donation.assigned_ngo and donation.assigned_ngo.user_id:
        create_event_notification(
            db=db,
            user_id=donation.assigned_ngo.user_id,
            event_type="ADMIN_INTERVENTION",
            donation_id=donation.id,
            extra_message=f"Admin intervention applied: {payload.reason_code.replace('_', ' ').title()}."
        )

    return AdminInterventionActionResponse(
        success=True,
        donation_id=donation.id,
        message=f"Admin intervention successfully recorded for Donation #{donation.id}.",
        audit_log_id=audit_entry.id if audit_entry else None
    )

# ── 5. NGO INTAKE CAPACITY STATUS ────────────────────────────────────────────

@router.get("/ngos/capacity", response_model=List[NGOCapacityItemResponse])
def get_all_ngo_capacities(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns real-time receiving capacity utilization for all partner NGOs.
    """
    ngos = db.query(NGO).filter(NGO.is_verified == True).all()
    results = []

    for n in ngos:
        max_cap = float(n.capacity or 500.0)
        cur_cap = float(n.current_capacity or 0.0)
        rem_cap = max(0.0, max_cap - cur_cap)
        util_pct = round((cur_cap / max_cap) * 100.0, 1) if max_cap > 0 else 0.0

        status_color = "GREEN"
        if util_pct >= 90.0:
            status_color = "RED"
        elif util_pct >= 70.0:
            status_color = "AMBER"

        results.append(NGOCapacityItemResponse(
            id=n.id,
            organization_name=n.organization_name,
            address=n.address or "Bangalore Center",
            current_capacity=cur_cap,
            max_capacity=max_cap,
            remaining_capacity=rem_cap,
            utilization_percent=util_pct,
            is_verified=n.is_verified,
            is_open=bool(n.is_open if hasattr(n, 'is_open') else True),
            status_color=status_color
        ))

    return results

# ── 6. TODAY'S FOOD CATEGORY BREAKDOWN ───────────────────────────────────────

@router.get("/category-breakdown", response_model=AdminCategoryBreakdownResponse)
def get_admin_food_category_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Provides an operational summary of food categories rescued today.
    """
    donations = db.query(FoodDonation).all()
    cat_map = {}
    total_meals = 0.0

    for d in donations:
        cat = d.food_category or "Cooked Food"
        qty = float(d.quantity)
        total_meals += qty

        if cat not in cat_map:
            cat_map[cat] = {"count": 0, "total_meals": 0.0}
        cat_map[cat]["count"] += 1
        cat_map[cat]["total_meals"] += qty

    categories = []
    for cat_name, val in cat_map.items():
        pct = round((val["total_meals"] / total_meals * 100.0), 1) if total_meals > 0 else 0.0
        categories.append(AdminCategoryBreakdownItem(
            category=cat_name,
            count=val["count"],
            total_meals=val["total_meals"],
            percentage=pct
        ))

    categories.sort(key=lambda x: x.total_meals, reverse=True)

    return AdminCategoryBreakdownResponse(
        total_meals=total_meals,
        categories=categories
    )

# ── 7. SPATIAL WASTE HEATMAP ─────────────────────────────────────────────────

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

# ── 8. INTERVENTIONS QUEUE (LEGACY COMPATIBILITY) ────────────────────────────

@router.get("/interventions", response_model=AdminInterventionsResponse)
def get_donations_requiring_intervention(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Identifies all donations requiring administrative intervention to prevent food waste.
    """
    now = datetime.now(timezone.utc)
    active_donations = db.query(FoodDonation).filter(
        FoodDonation.status.in_(["pending", "accepted", "volunteer_assigned", "pickup_failed", "delivery_failed"])
    ).all()

    items = []
    urgent_count = 0
    total_at_risk = 0.0

    for d in active_donations:
        expiry = d.expiry_time
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        time_left_hours = (expiry - now).total_seconds() / 3600.0
        time_left_hours = max(0.0, round(time_left_hours, 2))

        intervention_type = None
        reason = None
        suggested_action = None

        if d.status == "pickup_failed":
            intervention_type = "PICKUP_FAILED"
            reason = f"Volunteer pickup failed: {d.failure_reason or 'No reason provided'}"
            suggested_action = "Re-assign to alternative nearby volunteer or coordinate direct NGO pickup."
        elif d.status == "delivery_failed":
            intervention_type = "DELIVERY_FAILED"
            reason = f"Delivery failed: {d.failure_reason or 'Transit impediment'}"
            suggested_action = "Contact assigned NGO and volunteer immediately."
        elif time_left_hours <= 1.0 and d.status in ["pending", "accepted"]:
            intervention_type = "DEADLINE_APPROACHING"
            reason = f"Only {time_left_hours:.1f}h remaining before expiry."
            suggested_action = "Initiate emergency broadcast dispatch."
        elif d.status == "pending" and (time_left_hours <= 2.5 or d.is_emergency):
            intervention_type = "URGENT_NO_NGO"
            reason = f"Surplus food ({d.quantity} {d.quantity_unit}) has no receiving NGO with {time_left_hours:.1f}h left."
            suggested_action = "Trigger expanded NGO radius broadcast."
        elif d.status == "accepted" and d.assigned_volunteer_id is None and time_left_hours <= 2.5:
            intervention_type = "URGENT_NO_VOLUNTEER"
            reason = f"NGO accepted but no volunteer dispatched with {time_left_hours:.1f}h left."
            suggested_action = "Dispatch high-priority volunteer match offer."

        if intervention_type:
            total_at_risk += float(d.quantity)
            if time_left_hours <= 2.0 or d.is_emergency:
                urgent_count += 1

            pickup_area = d.pickup_address.split(",")[-1].strip() if "," in d.pickup_address else d.pickup_address[:30]

            items.append(AdminInterventionItem(
                donation_id=d.id,
                food_name=d.food_name,
                food_category=d.food_category,
                quantity=d.quantity,
                quantity_unit=d.quantity_unit,
                status=d.status,
                is_emergency=d.is_emergency,
                intervention_type=intervention_type,
                reason=reason,
                time_remaining_hours=time_left_hours,
                food_at_risk_meals=float(d.quantity),
                suggested_action=suggested_action,
                created_at=d.created_at,
                pickup_area=pickup_area
            ))

    return AdminInterventionsResponse(
        total_interventions_needed=len(items),
        total_food_at_risk_meals=total_at_risk,
        urgent_count=urgent_count,
        items=items
    )

# ── 9. A7 AUDIT LOG VIEWER ───────────────────────────────────────────────────

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Read-only security log for operational auditing (A7).
    Never exposes sensitive tokens or OTP values.
    """
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        query = query.filter(AuditLog.action == action)
    if status:
        query = query.filter(AuditLog.status == status)
    logs = query.limit(limit).all()
    return [
        {
            "id": log.id,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "user_id": log.user_id,
            "actor": log.user.name if log.user else (f"User #{log.user_id}" if log.user_id else "System"),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "status": log.status,
            "details": log.details
        }
        for log in logs
    ]




