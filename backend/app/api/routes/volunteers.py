from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import secrets
from app.db.session import get_db
from app.models.models import (
    User, VolunteerAssignment, FoodDonation, Notification, DonationHistory,
    NGO, MatchOffer, RescueClaimToken
)
from app.schemas.schemas import (
    UserResponse, VolunteerAssignmentResponse, VolunteerProfileUpdate,
    VerifyOtpRequest, VerifyQRRequest, DonationFailureRequest,
    VolunteerRecommendationResponse, VolunteerLocationUpdateRequest, RescueTrackingResponse,
    RescueClaimTokenResponse, RescueClaimPreviewResponse, RescueClaimAcceptRequest,
    RescueClaimAcceptResponse, VolunteerAccountUpgradeRequest
)
from app.core.dependencies import get_current_user, require_role
from app.core.security import hash_password, create_access_token
from app.services.security_service import log_audit_event, validate_donation_transition, log_rescue_operation
from app.services.recommendation_service import recommend_volunteers
from app.services.notification_service import create_notification, create_event_notification
from app.services.otp_service import generate_pickup_otp, send_pickup_otp_sms
from app.services.live_tracking_service import live_tracking_service
from app.services.state_machine_service import (
    transition_donation_state,
    transition_donation_status,
    transition_assignment_status,
    DonationStatus,
    AssignmentStatus,
)
from app.services.food_rescue_window_service import RescueUrgencyLevel
from app.services.proactive_dispatch_service import ProactiveDispatchService, _extract_approximate_area
from app.services.rematching_service import RematchingService

router = APIRouter(prefix="/volunteers", tags=["Volunteers"])

@router.get("", response_model=List[UserResponse])
def get_volunteers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    return volunteers

@router.get("/matches/{donation_id}", response_model=List[VolunteerRecommendationResponse])
def get_volunteer_matches_for_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns prioritized volunteer matches who are active and have sufficient carrying capacity.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    
    matches = recommend_volunteers(db, donation)
    return [VolunteerRecommendationResponse(**m) for m in matches]

@router.get("/available", response_model=List[UserResponse])
def get_available_volunteers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

@router.put("/profile", response_model=UserResponse)
def update_volunteer_profile(
    profile_in: VolunteerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    if profile_in.vehicle_type is not None:
        current_user.vehicle_type = profile_in.vehicle_type
    if profile_in.carrying_capacity is not None:
        current_user.carrying_capacity = profile_in.carrying_capacity
    if profile_in.is_active is not None:
        current_user.is_active = profile_in.is_active
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/assignments", response_model=VolunteerAssignmentResponse)
def create_volunteer_assignment(
    donation_id: int,
    volunteer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin", "volunteer"]))
):
    if volunteer_id is None:
        if current_user.role == "volunteer":
            volunteer_id = current_user.id
        else:
            raise HTTPException(status_code=400, detail="volunteer_id query parameter is required.")

    # ── Concurrency protection: lock row before checking state ─────────────
    donation = db.query(FoodDonation).filter(
        FoodDonation.id == donation_id
    ).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # ── State Machine Guard: Cannot assign expired/completed/cancelled donations ───
    if donation.status in ["expired", "completed", "cancelled", "delivered"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Donation is no longer eligible for pickup assignment (status: '{donation.status}')."
        )

    # ── Branch Guard: Direct NGO Self-Pickup prohibits volunteer courier dispatch ───
    if donation.pickup_mode == "self_pickup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This donation is scheduled for direct NGO self-pickup. Volunteer courier assignment is not permitted unless the NGO requests volunteer support."
        )

    # ── Execution-Time ERW Re-evaluation ──────────────────────────────────────
    now_eval = datetime.now(timezone.utc)
    urgency_eval = ProactiveDispatchService.evaluate_donation_urgency(db, donation, reference_time=now_eval)
    if (
        urgency_eval.get("urgency_level") == RescueUrgencyLevel.RESCUE_WINDOW_ENDED
        or (donation.remaining_minutes is not None and donation.remaining_minutes <= 0)
        or donation.status == "expired"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advisory rescue window has ended. Volunteer courier cannot be assigned."
        )

    volunteer = db.query(User).filter(User.id == volunteer_id, User.role == "volunteer").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer user not found.")

    # ── Single Active Task Guard: A volunteer can only have one active task at a time ──
    active_assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.volunteer_id == volunteer.id,
        VolunteerAssignment.donation_id != donation.id,
        VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
    ).first()
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer already has an active rescue task in progress. You may only hold one active assignment at a time."
        )

    # ── Capacity Safeguard: Validate volunteer carrying capacity ───────────
    vol_cap = volunteer.carrying_capacity or 50
    if donation.quantity > vol_cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Donation quantity ({donation.quantity} {donation.quantity_unit}) exceeds volunteer carrying capacity ({vol_cap} meals for vehicle '{volunteer.vehicle_type or 'bike'}'). Please assign a volunteer with adequate vehicle capacity."
        )

    # ── Logistics Feasibility Hard Gate: Never dispatch food on an infeasible route ──
    from app.services.rematching_service import RematchingService
    feasibility = RematchingService.evaluate_assignment_feasibility(
        db=db,
        donation=donation,
        volunteer=volunteer,
        reference_time=now_eval
    )
    if not feasibility["is_feasible"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Assignment rejected: Route is logistics infeasible. "
                f"Total mission time ({feasibility['total_required_minutes']}m) exceeds remaining rescue window ({feasibility['remaining_window_minutes']}m). "
                f"Courier reliability cannot override rescue-window infeasibility."
            )
        )

    # Idempotency & Concurrency: reject if already assigned to prevent race conditions & duplicate assignments
    if donation.assigned_volunteer_id is not None and donation.assigned_volunteer_id != volunteer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This donation has already been assigned to another volunteer."
        )

    existing_assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.status.in_(["assigned", "accepted", "collected"])
    ).first()
    if existing_assignment and existing_assignment.volunteer_id != volunteer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This donation has already been assigned to another volunteer."
        )

    if not existing_assignment:
        assignment = VolunteerAssignment(
            donation_id=donation.id,
            volunteer_id=volunteer.id,
            status="assigned"
        )
        db.add(assignment)
    else:
        assignment = existing_assignment
        assignment.volunteer_id = volunteer.id
        transition_assignment_status(
            db, assignment, "assigned",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Assignment renewed for volunteer {volunteer.name}"
        )

    donation.assigned_volunteer_id = volunteer.id
    transition_donation_status(
        db, donation, "volunteer_assigned",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Volunteer {volunteer.name} assigned to pickup"
    )

    create_event_notification(
        db=db,
        user_id=volunteer.id,
        event_type="VOLUNTEER_ASSIGNED",
        donation_id=donation.id,
        extra_message=f"You have been assigned to pick up '{donation.food_name}' at {donation.pickup_address}."
    )
    create_event_notification(
        db=db,
        user_id=donation.donor_id,
        event_type="VOLUNTEER_ASSIGNED",
        donation_id=donation.id,
        extra_message=f"Volunteer {volunteer.name} has been assigned to pick up your donation."
    )
    if donation.assigned_ngo_id:
        ngo_record = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first()
        if ngo_record and ngo_record.user_id:
            create_event_notification(
                db=db,
                user_id=ngo_record.user_id,
                event_type="VOLUNTEER_ASSIGNED",
                donation_id=donation.id,
                extra_message=f"Volunteer {volunteer.name} has been assigned to pick up donation #{donation.id} for your organization."
            )

    now = datetime.now(timezone.utc)
    vol_offer = db.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_id == volunteer.id,
        MatchOffer.candidate_type == "volunteer"
    ).first()
    if vol_offer:
        vol_offer.status = "accepted"
        vol_offer.responded_at = now
        if vol_offer.offered_at:
            offered_at = vol_offer.offered_at
            if offered_at.tzinfo is None:
                offered_at = offered_at.replace(tzinfo=timezone.utc)
            vol_offer.response_time_seconds = (now - offered_at).total_seconds()
    else:
        vol_offer = MatchOffer(
            donation_id=donation.id,
            candidate_id=volunteer.id,
            candidate_type="volunteer",
            score=100.0,
            status="accepted",
            wave_number=donation.current_alert_wave or 2,
            offered_at=now,
            responded_at=now,
            response_time_seconds=0.0
        )
        db.add(vol_offer)

    # Cancel other outstanding volunteer offers for this donation
    db.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.id != (vol_offer.id if vol_offer else 0),
        MatchOffer.candidate_type == "volunteer",
        MatchOffer.status == "offered"
    ).update({"status": "cancelled", "responded_at": now})

    db.commit()
    db.refresh(assignment)

    log_audit_event(db, action="volunteer_assigned", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success",
                    details=f"Volunteer {volunteer.name} assigned to donation {donation.id}")

    return assignment

@router.post("/verify-otp", response_model=VolunteerAssignmentResponse)
def verify_pickup_otp(
    verify_in: VerifyOtpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """
    Backend-verified pickup confirmation via 6-digit OTP.
    Security: assignment ownership + OTP match + expiry + single-use replay protection.
    """
    from app.services.otp_service import verify_pickup_otp, _otp_verification_lock

    with _otp_verification_lock:
        db.expire_all()
        try:
            donation = db.query(FoodDonation).filter(FoodDonation.id == verify_in.donation_id).with_for_update().first()
        except Exception:
            donation = db.query(FoodDonation).filter(FoodDonation.id == verify_in.donation_id).first()
        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found.")

        # ── EARLY: OTP replay protection (checked before assignment lookup) ────────
        # Must run first: if OTP was already consumed, always 409 regardless of assignment state.
        if donation.otp_used_at is not None or donation.status in ["collected", "in_transit", "delivered", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This OTP has already been used. Pickup already verified."
            )

        # ── 1. Volunteer assignment ownership check ────────────────────────────
        # ANY volunteer knowing the OTP is NOT sufficient — must be the ASSIGNED volunteer
        if current_user.role == "volunteer":
            assignment = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == donation.id,
                VolunteerAssignment.volunteer_id == current_user.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived"])
            ).first()
            if not assignment:
                log_audit_event(db, action="otp_unauthorized_attempt", user_id=current_user.id,
                                resource_type="donation", resource_id=donation.id, status_code="failed",
                                details=f"Unassigned volunteer {current_user.id} attempted OTP on donation {donation.id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not the assigned volunteer for this donation."
                )
        else:
            # Admin path — find assignment
            assignment = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == donation.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived"])
            ).first()

        # ── 2. Donation state validation ──────────────────────────────────────
        if donation.status not in ["volunteer_assigned", "accepted", "pickup_en_route", "arrived_at_donor"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Donation is not in a valid pickup state (current: '{donation.status}')."
            )

        # ── 3. Hardened OTP verification (handles hashing, timing-safe compare, expiry, token consumption) ──
        verify_pickup_otp(db, donation, verify_in.otp.strip(), current_user)

        # ── 4. Update assignment and donation status ──
        now = datetime.now(timezone.utc)
        if not assignment:
            assignment = VolunteerAssignment(
                donation_id=donation.id,
                volunteer_id=current_user.id,
                status="collected"
            )
            db.add(assignment)

        transition_assignment_status(
            db, assignment, "collected",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks="Pickup confirmed with OTP"
        )
        donation.assigned_volunteer_id = current_user.id
        transition_donation_status(
            db, donation, "collected",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Pickup verified securely with OTP by volunteer {current_user.name}"
        )

        create_event_notification(
            db=db,
            user_id=donation.donor_id,
            event_type="OTP_VERIFIED",
            donation_id=donation.id,
        )
        create_event_notification(
            db=db,
            user_id=donation.donor_id,
            event_type="PICKUP_COMPLETED",
            donation_id=donation.id,
        )
        create_event_notification(
            db=db,
            user_id=current_user.id,
            event_type="PICKUP_COMPLETED",
            donation_id=donation.id,
        )

        db.commit()
        db.refresh(assignment)

        log_audit_event(db, action="otp_verified", user_id=current_user.id,
                        resource_type="donation", resource_id=donation.id, status_code="success",
                        details=f"OTP pickup verified for donation {donation.id}")
        log_rescue_operation(
            db, action="collected", donation_id=donation.id,
            user_id=current_user.id, old_status="arrived_at_donor", new_status="collected",
            remarks=f"Pickup verified securely with OTP by volunteer {current_user.name}",
            details=f"Donation #{donation.id} collected via OTP handover"
        )

        return assignment

@router.post("/verify-qr", response_model=VolunteerAssignmentResponse)
def verify_pickup_qr(
    verify_in: VerifyQRRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """
    Backend-verified pickup confirmation via secure QR Token.
    Security: assignment ownership + QR match + expiry + single-use replay protection.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == verify_in.donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # ── 1. Volunteer assignment ownership check ────────────────────────────
    if current_user.role == "volunteer":
        assignment = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == donation.id,
            VolunteerAssignment.volunteer_id == current_user.id,
            VolunteerAssignment.status.in_(["assigned", "accepted"])
        ).first()
        if not assignment:
            log_audit_event(db, action="qr_unauthorized_attempt", user_id=current_user.id,
                            resource_type="donation", resource_id=donation.id, status_code="failed",
                            details=f"Unassigned volunteer {current_user.id} attempted QR on donation {donation.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned volunteer for this donation."
            )
    else:
        assignment = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == donation.id,
            VolunteerAssignment.status.in_(["assigned", "accepted"])
        ).first()

    # ── 2. Donation state validation ──────────────────────────────────────
    if donation.status not in ["volunteer_assigned", "accepted"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Donation is not in a valid pickup state (current: '{donation.status}')."
        )

    # ── 3. QR replay protection: single-use check ─────────────────────────
    if donation.qr_used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This QR code has already been used. Pickup already verified."
        )

    # ── 4. QR expiry check ─────────────────────────────────────────────
    if donation.qr_expiry:
        qr_expiry = donation.qr_expiry
        if qr_expiry.tzinfo is None:
            qr_expiry = qr_expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > qr_expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR code has expired. Please contact the donor for a new verification code."
            )

    # ── 5. QR token correctness check ────────────────────────────────────
    if not donation.qr_code_token or donation.qr_code_token.strip() != verify_in.qr_token.strip():
        log_audit_event(db, action="qr_failed", user_id=current_user.id,
                        resource_type="donation", resource_id=donation.id, status_code="failed")
        raise HTTPException(status_code=400, detail="Invalid QR Verification Token.")

    # ── All checks passed — consume QR (replay protection) and update state ──
    now = datetime.now(timezone.utc)
    donation.qr_used_at = now  # Mark as consumed — prevents replay

    if not assignment:
        assignment = VolunteerAssignment(
            donation_id=donation.id,
            volunteer_id=current_user.id,
            status="collected"
        )
        db.add(assignment)

    transition_assignment_status(
        db, assignment, "collected",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks="Pickup confirmed via QR"
    )
    donation.assigned_volunteer_id = current_user.id
    transition_donation_status(
        db, donation, "collected",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Pickup verified via QR Code scan by volunteer {current_user.name}"
    )

    create_event_notification(
        db=db,
        user_id=donation.donor_id,
        event_type="OTP_VERIFIED",
        donation_id=donation.id,
    )
    create_event_notification(
        db=db,
        user_id=donation.donor_id,
        event_type="PICKUP_COMPLETED",
        donation_id=donation.id,
    )
    create_event_notification(
        db=db,
        user_id=current_user.id,
        event_type="PICKUP_COMPLETED",
        donation_id=donation.id,
    )

    db.commit()
    db.refresh(assignment)

    log_audit_event(db, action="qr_verified", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success",
                    details=f"QR pickup verified for donation {donation.id}")

    return assignment

@router.post("/report-failure", response_model=VolunteerAssignmentResponse)
def report_task_failure(
    failure_in: DonationFailureRequest,
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """
    Handles Failure States: pickup_failed, delivery_failed.
    Reasons: donor_unavailable, volunteer_rejected, food_expired, ngo_closed, incorrect_location, vehicle_issue.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.volunteer_id == current_user.id
    ).first()

    status_name = failure_in.failure_type.lower()
    if status_name not in ["pickup_failed", "delivery_failed"]:
        status_name = "pickup_failed"

    reason_str = f"{failure_in.reason}: {failure_in.remarks or ''}".strip()
    donation.failure_reason = reason_str

    transition_donation_status(
        db, donation, status_name,
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Task failure reported: {reason_str}"
    )

    if not assignment:
        assignment = VolunteerAssignment(
            donation_id=donation.id,
            volunteer_id=current_user.id,
            status="failed",
            failure_reason=reason_str
        )
        db.add(assignment)
        db.flush()
    else:
        transition_assignment_status(
            db, assignment, "failed",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=reason_str
        )
        assignment.failure_reason = reason_str

    # Adjust volunteer metrics according to cancellation reason (Section 21)
    # Excused reasons (real breakdown, medical emergency, venue/donor issues) do NOT penalize reliability score
    excused_keywords = [
        "breakdown", "vehicle", "puncture", "flat", "engine", "accident", "broken",
        "emergency", "medical", "hospital", "donor_unavailable", "donor unavailable",
        "premises closed", "venue closed", "ngo closed", "food_spoiled", "food spoiled",
        "food_expired", "food expired", "incorrect_location", "no longer available"
    ]
    is_excused = any(k in reason_str.lower() for k in excused_keywords)

    if not is_excused:
        current_user.failed_deliveries = (current_user.failed_deliveries or 0) + 1
        total = (current_user.completed_deliveries or 0) + current_user.failed_deliveries
        current_user.reliability_score = round(((current_user.completed_deliveries or 0) / float(total)) * 100, 1)

    # Alert Donor & NGO
    db.add(Notification(
        user_id=donation.donor_id,
        title=f"Delivery Alert: {status_name.replace('_', ' ').title()}",
        message=f"Issue reported on '{donation.food_name}': {donation.failure_reason}",
        type="alert",
        related_donation_id=donation.id
    ))

    # Dynamic Rematching: Automatically initiate backup courier search on vehicle breakdown or operational failure
    # Do NOT rematch if failure is due to donor being unavailable, venue closed, or food condition
    donor_or_venue_issue = any(k in reason_str.lower() for k in ["donor_unavailable", "premises closed", "venue closed", "food_spoiled", "food_expired", "incorrect_location", "no longer available"])
    if not donor_or_venue_issue and donation.status not in ["expired", "delivered", "completed", "cancelled"]:
        from app.services.rematching_service import RematchingService
        trigger = (
            "VEHICLE_BREAKDOWN"
            if any(w in reason_str.lower() for w in ["vehicle", "breakdown", "tyre", "puncture", "engine", "flat", "accident", "broken"])
            else "COURIER_FAILED"
        )
        RematchingService.attempt_dynamic_rematch(
            db=db,
            donation=donation,
            trigger=trigger,
            reason=f"Courier reported failure ({trigger}): {reason_str}"
        )

    db.commit()
    db.refresh(assignment)
    return assignment

@router.put("/assignments/{assignment_id}", response_model=VolunteerAssignmentResponse)
def update_volunteer_assignment_status(
    assignment_id: int,
    status_update: str, # accepted, collected, delivered, cancelled, en_route, arrived, in_transit
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "ngo", "admin"]))
):
    if assignment_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID: ID must be a positive integer greater than 0."
        )

    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        if current_user.role == "volunteer":
            assignment = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == assignment_id,
                VolunteerAssignment.volunteer_id == current_user.id
            ).order_by(VolunteerAssignment.id.desc()).first()
            if not assignment:
                other_assignment = db.query(VolunteerAssignment).filter(
                    VolunteerAssignment.donation_id == assignment_id
                ).first()
                if other_assignment:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not authorized to modify this assignment."
                    )
        else:
            assignment = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == assignment_id
            ).order_by(VolunteerAssignment.id.desc()).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    # Ownership check: volunteer can only update their own assignment
    if current_user.role == "volunteer" and assignment.volunteer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this assignment."
        )

    now = datetime.now(timezone.utc)
    target_status = status_update.lower()

    if target_status == "accepted":
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            now_eval = datetime.now(timezone.utc)
            urgency_eval = ProactiveDispatchService.evaluate_donation_urgency(db, donation, reference_time=now_eval)
            if (
                urgency_eval.get("urgency_level") == RescueUrgencyLevel.RESCUE_WINDOW_ENDED
                or (donation.remaining_minutes is not None and donation.remaining_minutes <= 0)
                or donation.status == "expired"
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Advisory rescue window has ended. Assignment can no longer be accepted."
                )

        assignment.accepted_at = now
        transition_assignment_status(
            db, assignment, "accepted",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Assignment accepted by volunteer {current_user.name}"
        )
        if donation:
            donation.assigned_volunteer_id = assignment.volunteer_id
            transition_donation_status(
                db, donation, "volunteer_assigned",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Volunteer {current_user.name} accepted assignment"
            )
    elif target_status in ["en_route", "pickup_en_route"]:
        transition_assignment_status(
            db, assignment, "en_route",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Volunteer {current_user.name} en route for pickup"
        )
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            transition_donation_status(
                db, donation, "pickup_en_route",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Volunteer {current_user.name} en route for pickup"
            )
            donor = db.query(User).filter(User.id == donation.donor_id).first()
            donor_lang = (donor.preferred_language if donor else "en") or "en"
            create_event_notification(
                db=db,
                user_id=donation.donor_id,
                event_type="VOLUNTEER_ON_THE_WAY",
                donation_id=donation.id,
                lang=donor_lang,
            )
            log_audit_event(db, action="volunteer_en_route", user_id=current_user.id,
                            resource_type="donation", resource_id=donation.id, status_code="success",
                            details=f"Volunteer {current_user.name} en route for pickup on donation {donation.id}")
    elif target_status in ["arrived", "arrived_at_donor"]:
        transition_assignment_status(
            db, assignment, "arrived",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Volunteer {current_user.name} arrived at donor location"
        )
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            transition_donation_status(
                db, donation, "arrived_at_donor",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Volunteer {current_user.name} arrived at donor location"
            )
            donor = db.query(User).filter(User.id == donation.donor_id).first()
            donor_lang = (donor.preferred_language if donor else "en") or "en"
            # Use event-based notification (deep-link routes to pickup OTP screen)
            create_event_notification(
                db=db,
                user_id=donation.donor_id,
                event_type="VOLUNTEER_ARRIVED",
                donation_id=donation.id,
                lang=donor_lang,
            )
            # Auto-generate and send pickup OTP via SMS to verified donor phone
            try:
                vol_id = assignment.volunteer_id
                plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor, volunteer_id=vol_id)
                if donor and donor.phone_verified:
                    send_pickup_otp_sms(db, plaintext_otp, otp_record, donor)
                    create_event_notification(
                        db=db,
                        user_id=donation.donor_id,
                        event_type="OTP_SMS_SENT",
                        donation_id=donation.id,
                        lang=donor_lang,
                    )
                else:
                    import logging
                    logging.getLogger("smart_food_rescue").info(
                        f"[OTP] Skipped SMS for donation {donation.id} — donor phone not verified"
                    )
            except Exception as otp_exc:
                import logging
                logging.getLogger("smart_food_rescue").warning(
                    f"[OTP] OTP generation/send failed for donation {donation.id}: {otp_exc}"
                )
            log_audit_event(db, action="volunteer_arrived_at_donor", user_id=current_user.id,
                            resource_type="donation", resource_id=donation.id, status_code="success",
                            details=f"Volunteer {current_user.name} arrived at donor location for donation {donation.id}")
    elif target_status in ["in_transit", "transit"]:
        transition_assignment_status(
            db, assignment, "in_transit",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Volunteer {current_user.name} in transit with food"
        )
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            transition_donation_status(
                db, donation, "in_transit",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Volunteer {current_user.name} in transit with food"
            )
    elif target_status == "collected":
        assignment.collected_at = now
        transition_assignment_status(
            db, assignment, "collected",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Food collected by volunteer {current_user.name}"
        )
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            transition_donation_status(
                db, donation, "collected",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Food collected by volunteer {current_user.name}"
            )
            db.add(Notification(
                user_id=donation.donor_id,
                title="Food collected",
                message="Your donated food has been collected and is on its way to the NGO.",
                type="food_collected",
                related_donation_id=donation.id
            ))
    elif target_status == "delivered":
        assignment.delivered_at = now
        transition_assignment_status(
            db, assignment, "delivered",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Delivered to NGO by volunteer {current_user.name}"
        )
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            transition_donation_status(
                db, donation, "delivered",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Delivered to NGO by volunteer {current_user.name}"
            )
            db.add(Notification(
                user_id=donation.donor_id,
                title="Food delivered",
                message="Your donation has reached the receiving NGO.",
                type="food_delivered",
                related_donation_id=donation.id
            ))
    elif target_status == "cancelled":
        transition_assignment_status(
            db, assignment, "cancelled",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Assignment cancelled by {current_user.name}"
        )
    else:
        transition_assignment_status(
            db, assignment, target_status,
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Assignment status updated to {target_status}"
        )

    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/assignments/{assignment_id}/start-pickup", response_model=VolunteerAssignmentResponse)
def start_pickup(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer is actively traveling to donor location for pickup."""
    return update_volunteer_assignment_status(assignment_id, "en_route", db, current_user)

@router.post("/assignments/{assignment_id}/arrived", response_model=VolunteerAssignmentResponse)
def signal_arrival_at_donor(
    assignment_id: int,
    method: str = Query("gps", description="Arrival verification method: gps, manual_here, donor_confirmed, admin_override"),
    reason: Optional[str] = Query(None, description="Reason if manual/fallback arrival verification is used"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer has physically arrived at donor location, triggering donor arrival notification."""
    res = update_volunteer_assignment_status(assignment_id, "arrived", db, current_user)
    # Master Prompt Section 14: Log audited arrival details
    log_audit_event(
        db, action="volunteer_arrival_verified", user_id=current_user.id,
        resource_type="assignment", resource_id=res.id, status_code="success",
        details=f"Arrival verified via method '{method}' (reason: {reason or 'Standard GPS arrival'}) for donation {res.donation_id}"
    )
    return res

@router.post("/donations/{donation_id}/start-pickup", response_model=VolunteerAssignmentResponse)
def start_pickup_by_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer is actively traveling to donor location for pickup (addressed by donation ID)."""
    return update_volunteer_assignment_status(donation_id, "en_route", db, current_user)

@router.post("/donations/{donation_id}/arrived", response_model=VolunteerAssignmentResponse)
def signal_arrival_by_donation(
    donation_id: int,
    method: str = Query("gps"),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer has arrived at donor location (addressed by donation ID)."""
    return signal_arrival_at_donor(donation_id, method=method, reason=reason, db=db, current_user=current_user)

@router.post("/donations/{donation_id}/in-transit", response_model=VolunteerAssignmentResponse)
def signal_in_transit_by_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer is in transit to receiving NGO."""
    return update_volunteer_assignment_status(donation_id, "in_transit", db, current_user)

@router.post("/donations/{donation_id}/deliver", response_model=VolunteerAssignmentResponse)
def signal_delivered_by_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer has delivered the food to receiving NGO."""
    return update_volunteer_assignment_status(donation_id, "delivered", db, current_user)

@router.get("/assignments/{assignment_id}", response_model=VolunteerAssignmentResponse)
def get_volunteer_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if assignment_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID: ID must be a positive integer greater than 0."
        )

    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    # Ownership check: Volunteer can only access their own assignment
    if current_user.role == "volunteer" and assignment.volunteer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this assignment.")
    elif current_user.role not in ["volunteer", "admin", "ngo"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this assignment.")

    return assignment

@router.post("/assignments/{assignment_id}/accept", response_model=VolunteerAssignmentResponse)
def accept_volunteer_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Volunteer formally accepts a dispatched food rescue task."""
    if assignment_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID: ID must be a positive integer greater than 0."
        )

    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    if current_user.role == "volunteer" and assignment.volunteer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to accept this assignment.")

    donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
    if donation and donation.pickup_mode == "self_pickup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This donation is scheduled for direct NGO self-pickup. Volunteer courier acceptance is not permitted."
        )
    if donation:
        donation.assigned_volunteer_id = assignment.volunteer_id
        transition_donation_status(
            db, donation, "volunteer_assigned",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Volunteer {current_user.name} accepted assignment"
        )

    now = datetime.now(timezone.utc)
    assignment.accepted_at = now
    transition_assignment_status(
        db, assignment, "accepted",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Volunteer {current_user.name} accepted assignment"
    )

    if donation:
        # Update MatchOffer for the volunteer
        winning_offer = db.query(MatchOffer).filter(
            MatchOffer.donation_id == donation.id,
            MatchOffer.candidate_id == current_user.id,
            MatchOffer.candidate_type == "volunteer"
        ).first()
        if winning_offer:
            winning_offer.status = "accepted"
            winning_offer.responded_at = now
            if winning_offer.offered_at:
                offered_at = winning_offer.offered_at
                if offered_at.tzinfo is None:
                    offered_at = offered_at.replace(tzinfo=timezone.utc)
                winning_offer.response_time_seconds = (now - offered_at).total_seconds()
        else:
            winning_offer = MatchOffer(
                donation_id=donation.id,
                candidate_id=current_user.id,
                candidate_type="volunteer",
                score=100.0,
                status="accepted",
                wave_number=donation.current_alert_wave or 2,
                offered_at=now,
                responded_at=now,
                response_time_seconds=0.0
            )
            db.add(winning_offer)

        # Cancel all other outstanding volunteer offers for this donation
        db.query(MatchOffer).filter(
            MatchOffer.donation_id == donation.id,
            MatchOffer.id != (winning_offer.id if winning_offer else 0),
            MatchOffer.candidate_type == "volunteer",
            MatchOffer.status == "offered"
        ).update({"status": "cancelled", "responded_at": now})

    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/assignments/{assignment_id}/reject")
def reject_volunteer_assignment(
    assignment_id: int,
    reason: Optional[str] = Query("Volunteer unavailable", alias="reason"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """
    Volunteer rejects assignment.
    Automatically unassigns donation and executes fallback volunteer search.
    """
    if assignment_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID: ID must be a positive integer greater than 0."
        )

    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    if current_user.role == "volunteer" and assignment.volunteer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to reject this assignment.")

    donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
    if donation:
        donation.assigned_volunteer_id = None
        # Keep donation in accepted state awaiting another volunteer
        if donation.status == "volunteer_assigned":
            transition_donation_status(
                db, donation, "accepted",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Volunteer rejected assignment: {reason}"
            )

    transition_assignment_status(
        db, assignment, "cancelled",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Assignment rejected: {reason}"
    )
    assignment.failure_reason = reason

    now = datetime.now(timezone.utc)
    vol_offer = db.query(MatchOffer).filter(
        MatchOffer.donation_id == (donation.id if donation else assignment.donation_id),
        MatchOffer.candidate_id == current_user.id,
        MatchOffer.candidate_type == "volunteer",
        MatchOffer.status == "offered"
    ).first()
    if vol_offer:
        vol_offer.status = "rejected"
        vol_offer.responded_at = now
        if vol_offer.offered_at:
            offered_at = vol_offer.offered_at
            if offered_at.tzinfo is None:
                offered_at = offered_at.replace(tzinfo=timezone.utc)
            vol_offer.response_time_seconds = (now - offered_at).total_seconds()

    # Fallback Matching & Dynamic Rematching: Automatically dispatch top feasible backup volunteer
    fallback_notified = False
    rematch_result = None
    if donation:
        from app.services.rematching_service import RematchingService
        rematch_result = RematchingService.attempt_dynamic_rematch(
            db=db,
            donation=donation,
            trigger="COURIER_CANCELLED",
            reason=f"Volunteer rejected assignment: {reason}"
        )
        if rematch_result.get("status") == "REMATCHED":
            fallback_notified = True
        else:
            try:
                ProactiveDispatchService.dispatch_proactive_alerts(db, donation, force_dispatch=True)
                fallback_notified = True
            except Exception:
                pass

            if not fallback_notified:
                matches = recommend_volunteers(db, donation)
                for m in matches:
                    if m["volunteer_id"] != assignment.volunteer_id and m.get("is_feasible", True):
                        next_vol = db.query(User).filter(User.id == m["volunteer_id"]).first()
                        if next_vol and (next_vol.carrying_capacity or 50) >= donation.quantity:
                            create_notification(
                                db,
                                user_id=next_vol.id,
                                title="New Volunteer Pickup Opportunity",
                                message=f"Pickup available: '{donation.food_name}' ({donation.quantity} {donation.quantity_unit}).",
                                type="assignment",
                                related_donation_id=donation.id
                            )
                            fallback_notified = True
                            break

    db.commit()
    return {
        "detail": "Assignment rejected. Fallback volunteer search initiated.",
        "fallback_notified": fallback_notified,
        "rematch_result": rematch_result
    }

@router.post("/location")
def update_volunteer_location(
    loc_in: VolunteerLocationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """
    Real-time volunteer location telemetry update.
    Security: Volunteer can only update their own assigned rescue location.
    Updates coordinates, recalibrates honest travel ETA, and detects arrival proximity.
    """
    return live_tracking_service.update_volunteer_location(
        db=db,
        volunteer_user=current_user,
        latitude=loc_in.latitude,
        longitude=loc_in.longitude,
        donation_id=loc_in.donation_id,
        assignment_id=loc_in.assignment_id,
        speed_kmh=loc_in.speed_kmh,
        heading=loc_in.heading,
        battery_level=loc_in.battery_level
    )

@router.get("/active-task/tracking", response_model=RescueTrackingResponse)
def get_volunteer_active_task_tracking(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """
    Retrieves real-time operational tracking data for the volunteer's active task.
    """
    # Find active assignment
    active_assign = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.volunteer_id == current_user.id,
        VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
    ).order_by(VolunteerAssignment.id.desc()).first()

    if not active_assign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active food rescue task found for this volunteer."
        )

    return live_tracking_service.get_tracking_data(
        db=db,
        donation_id=active_assign.donation_id,
        current_user=current_user
    )


# ─── Frictionless First-Time Volunteer Claim Endpoints ───────────────────────

@router.post("/donations/{donation_id}/claim-token", response_model=RescueClaimTokenResponse)
def generate_rescue_claim_token(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "ngo", "admin", "volunteer"]))
):
    """
    Generates a secure, single-use, time-scoped shareable claim token for an active donation.
    Enables low-friction first-time volunteer rescue claims via shareable link.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if current_user.role == "donor" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this donation.")

    if donation.status in ["expired", "cancelled", "completed", "delivered", "volunteer_assigned", "collected"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate claim link: Donation status is '{donation.status}'."
        )

    if donation.pickup_mode == "self_pickup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This donation is scheduled for direct NGO self-pickup."
        )

    # Recalculate ERW
    now = datetime.now(timezone.utc)
    urgency_info = ProactiveDispatchService.evaluate_donation_urgency(db, donation, reference_time=now)
    remaining_mins = urgency_info.get("remaining_minutes", 0)
    if remaining_mins <= 0 or donation.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rescue window has ended. Cannot generate claim link."
        )

    # Invalidate existing active tokens for this donation to guarantee single active link
    db.query(RescueClaimToken).filter(
        RescueClaimToken.donation_id == donation.id,
        RescueClaimToken.is_active == True
    ).update({"is_active": False})

    # Generate cryptographically secure URL-safe token (32 bytes = 43 chars)
    token_str = secrets.token_urlsafe(32)
    # Expiry is minimum of 60 mins or remaining ERW
    token_ttl_mins = min(60, max(15, remaining_mins))
    expires_at = now + timedelta(minutes=token_ttl_mins)

    claim_token = RescueClaimToken(
        donation_id=donation.id,
        token=token_str,
        created_at=now,
        expires_at=expires_at,
        is_active=True
    )
    db.add(claim_token)
    db.commit()
    db.refresh(claim_token)

    log_audit_event(
        db, action="rescue_claim_token_generated", user_id=current_user.id,
        resource_type="donation", resource_id=donation.id, status_code="success",
        details=f"Claim token generated, valid for {token_ttl_mins}m (expires at {expires_at.isoformat()})"
    )

    return RescueClaimTokenResponse(
        claim_token=token_str,
        claim_url=f"/claim/{token_str}",
        donation_id=donation.id,
        expires_at=expires_at,
        remaining_minutes=remaining_mins,
        urgency_level=urgency_info.get("urgency_level", "URGENT")
    )


@router.get("/claims/{token}", response_model=RescueClaimPreviewResponse)
def get_rescue_claim_preview(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Public preview endpoint for shareable rescue links.
    Returns minimal, privacy-safe information for a volunteer to decide whether to accept.
    Security: NEVER exposes exact address, donor phone, or OTP.
    """
    now = datetime.now(timezone.utc)
    claim_token = db.query(RescueClaimToken).filter(RescueClaimToken.token == token).first()
    if not claim_token:
        raise HTTPException(status_code=404, detail="Invalid rescue claim link.")

    if not claim_token.is_active or claim_token.claimed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This rescue has already been claimed by another volunteer."
        )

    if claim_token.expires_at:
        exp = claim_token.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This rescue claim link has expired."
            )

    donation = db.query(FoodDonation).filter(FoodDonation.id == claim_token.donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Associated donation not found.")

    if donation.status in ["volunteer_assigned", "collected", "delivered", "completed"]:
        claim_token.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This rescue has already been claimed by another volunteer."
        )

    if donation.status in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This rescue is no longer available (status: {donation.status})."
        )

    # Recalculate ERW
    urgency_info = ProactiveDispatchService.evaluate_donation_urgency(db, donation, reference_time=now)
    remaining_mins = urgency_info.get("remaining_minutes", 0)
    if remaining_mins <= 0 or donation.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The estimated rescue window for this food has ended."
        )

    # Privacy-safe approximate neighborhood (coarse)
    neighborhood = _extract_approximate_area(donation.pickup_address)
    approx_lat = round(donation.latitude, 2) if donation.latitude is not None else None
    approx_lon = round(donation.longitude, 2) if donation.longitude is not None else None

    return RescueClaimPreviewResponse(
        claim_token=token,
        donation_id=donation.id,
        food_name=donation.food_name,
        food_category=donation.food_category,
        quantity=donation.quantity,
        quantity_unit=donation.quantity_unit,
        pickup_neighborhood=neighborhood,
        approx_latitude=approx_lat,
        approx_longitude=approx_lon,
        remaining_minutes=remaining_mins,
        urgency_level=urgency_info.get("urgency_level", "URGENT"),
        is_feasible=True,
        expires_at=claim_token.expires_at,
        status=donation.status,
        dietary_type=getattr(donation, "dietary_type", None) or "Prepared Meals"
    )


@router.post("/claims/{token}/accept", response_model=RescueClaimAcceptResponse)
def accept_rescue_claim(
    token: str,
    request: RescueClaimAcceptRequest,
    db: Session = Depends(get_db)
):
    """
    Low-friction first-time volunteer acceptance endpoint.
    Accepts minimal volunteer identity (name, phone, vehicle), validates feasibility & state,
    creates/associates volunteer, establishes VolunteerAssignment, invalidates token,
    and returns JWT credentials for immediate field execution.
    """
    now = datetime.now(timezone.utc)

    # ── 1. Atomic Lock on Claim Token ──────────────────────────────────────────
    claim_token = db.query(RescueClaimToken).filter(
        RescueClaimToken.token == token
    ).with_for_update().first()

    if not claim_token:
        raise HTTPException(status_code=404, detail="Invalid rescue claim link.")

    if not claim_token.is_active or claim_token.claimed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This rescue has already been claimed by another volunteer."
        )

    if claim_token.expires_at:
        exp = claim_token.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This rescue claim link has expired."
            )

    # ── 2. Atomic Lock on Food Donation ────────────────────────────────────────
    donation = db.query(FoodDonation).filter(
        FoodDonation.id == claim_token.donation_id
    ).with_for_update().first()

    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if donation.status in ["volunteer_assigned", "collected", "delivered", "completed"]:
        claim_token.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This rescue has already been claimed by another volunteer."
        )

    if donation.status in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This rescue is no longer available (status: {donation.status})."
        )

    if donation.pickup_mode == "self_pickup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This donation is scheduled for direct NGO self-pickup."
        )

    # ── 3. Recalculate ERW & Urgency ──────────────────────────────────────────
    urgency_info = ProactiveDispatchService.evaluate_donation_urgency(db, donation, reference_time=now)
    remaining_mins = urgency_info.get("remaining_minutes", 0)
    if remaining_mins <= 0 or donation.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advisory rescue window has ended. Volunteer cannot be assigned."
        )

    # ── 4. Capacity Check ─────────────────────────────────────────────────────
    capacity = request.carrying_capacity or 50
    if donation.quantity > capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Donation quantity ({donation.quantity} {donation.quantity_unit}) exceeds your vehicle carrying capacity ({capacity} meals)."
        )

    # ── 5. Create or Resolve Volunteer User ───────────────────────────────────
    cleaned_phone = "".join(c for c in request.phone if c.isdigit() or c == "+")
    if not cleaned_phone.startswith("+"):
        if len(cleaned_phone) == 10:
            phone_normalized = f"+91{cleaned_phone}"
        elif len(cleaned_phone) == 12 and cleaned_phone.startswith("91"):
            phone_normalized = f"+{cleaned_phone}"
        else:
            phone_normalized = f"+91{cleaned_phone}"
    else:
        phone_normalized = cleaned_phone

    # Search for existing user with normalized phone or raw phone (scoped to volunteer role)
    volunteer = db.query(User).filter(
        (User.phone_normalized == phone_normalized) | (User.phone == request.phone),
        User.role == "volunteer"
    ).first()

    if not volunteer:
        # Create minimal temporary volunteer account
        rnd_hex = secrets.token_hex(4)
        phone_digits = "".join(filter(str.isdigit, phone_normalized))
        phone_suffix = phone_digits[-6:] if len(phone_digits) >= 6 else phone_digits
        temp_email = f"vol_{phone_suffix}_{rnd_hex}@quickrescue.org"
        temp_pwd = hash_password(secrets.token_urlsafe(16))

        volunteer = User(
            name=request.name.strip(),
            email=temp_email,
            password_hash=temp_pwd,
            phone=request.phone,
            phone_normalized=phone_normalized,
            phone_verified=True,
            role="volunteer",
            vehicle_type=request.vehicle_type or "bike",
            carrying_capacity=capacity,
            latitude=request.current_lat,
            longitude=request.current_lon,
            is_active=True,
            reliability_score=95.0,
            completed_deliveries=0,
            failed_deliveries=0
        )
        db.add(volunteer)
        db.flush()
    else:
        if volunteer.role != "volunteer":
            volunteer.role = "volunteer"
        if request.vehicle_type:
            volunteer.vehicle_type = request.vehicle_type
        if capacity:
            volunteer.carrying_capacity = capacity
        if request.current_lat is not None:
            volunteer.latitude = request.current_lat
            volunteer.longitude = request.current_lon

    # ── Single Active Task Guard: A volunteer can only have one active task at a time ──
    if volunteer.id:
        active_assignment = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.volunteer_id == volunteer.id,
            VolunteerAssignment.donation_id != donation.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
        ).first()
        if active_assignment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Volunteer already has an active rescue task in progress. You may only hold one active assignment at a time."
            )

    # ── 6. Feasibility Check ──────────────────────────────────────────────────
    feasibility = RematchingService.evaluate_assignment_feasibility(
        db=db,
        donation=donation,
        volunteer=volunteer,
        reference_time=now
    )
    if not feasibility.get("is_feasible", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Assignment rejected: Route is logistics infeasible. "
                f"Total mission time ({feasibility.get('total_required_minutes', 0)}m) "
                f"exceeds remaining rescue window ({feasibility.get('remaining_window_minutes', 0)}m)."
            )
        )

    # ── 7. Create VolunteerAssignment & Update Donation State ─────────────────
    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer.id,
        status="assigned",
        assigned_at=now,
        accepted_at=now,
        last_known_lat=request.current_lat,
        last_known_lon=request.current_lon,
        current_eta_minutes=feasibility.get("courier_to_donor_mins", 15.0)
    )
    db.add(assignment)
    db.flush()

    donation.assigned_volunteer_id = volunteer.id
    transition_donation_status(
        db, donation, "volunteer_assigned",
        changed_by_user_id=volunteer.id,
        caller_role="volunteer",
        remarks=f"First-time volunteer {volunteer.name} accepted rescue via shareable claim link"
    )

    # Invalidate claim token (single-use)
    claim_token.claimed_at = now
    claim_token.claimed_by_user_id = volunteer.id
    claim_token.is_active = False

    # ── 8. Audit Logging & Notifications ─────────────────────────────────────
    log_audit_event(
        db, action="volunteer_claim_accepted", user_id=volunteer.id,
        resource_type="donation", resource_id=donation.id, status_code="success",
        details=f"Frictionless claim accepted by volunteer {volunteer.name} ({phone_normalized})"
    )

    create_event_notification(
        db=db,
        user_id=donation.donor_id,
        event_type="VOLUNTEER_ASSIGNED",
        donation_id=donation.id,
        extra_message=f"Volunteer {volunteer.name} has claimed your food rescue and is on the way."
    )
    create_event_notification(
        db=db,
        user_id=volunteer.id,
        event_type="VOLUNTEER_ASSIGNED",
        donation_id=donation.id,
        extra_message=f"You have accepted pickup for '{donation.food_name}' at {donation.pickup_address}."
    )
    if donation.assigned_ngo_id and donation.assigned_ngo:
        create_event_notification(
            db=db,
            user_id=donation.assigned_ngo.user_id,
            event_type="VOLUNTEER_ASSIGNED",
            donation_id=donation.id,
            extra_message=f"Volunteer {volunteer.name} has claimed the rescue delivery for your shelter."
        )

    # ── 9. Issue JWT Access Token for Immediate Mobile Auth ───────────────────
    access_token = create_access_token(
        data={"sub": str(volunteer.id), "role": "volunteer", "name": volunteer.name}
    )

    db.commit()
    db.refresh(assignment)
    db.refresh(volunteer)

    return RescueClaimAcceptResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(volunteer),
        assignment_id=assignment.id,
        donation_id=donation.id,
        status="volunteer_assigned",
        pickup_address=donation.pickup_address,
        current_eta_minutes=assignment.current_eta_minutes,
        remaining_minutes=remaining_mins,
        urgency_level=urgency_info.get("urgency_level", "URGENT"),
        message="Rescue claimed successfully. Pickup address revealed."
    )


@router.post("/upgrade-account", response_model=UserResponse)
def upgrade_volunteer_account(
    request: VolunteerAccountUpgradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer"]))
):
    """
    Optional full account creation after completing a rescue.
    Converts a lightweight/temporary volunteer record into a fully registered account.
    """
    email_clean = request.email.lower().strip()
    existing_user = db.query(User).filter(User.email == email_clean, User.id != current_user.id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    current_user.email = email_clean
    current_user.password_hash = hash_password(request.password)
    if request.preferred_language:
        current_user.preferred_language = request.preferred_language
    current_user.is_active = True

    db.commit()
    db.refresh(current_user)

    log_audit_event(
        db, action="volunteer_account_upgraded", user_id=current_user.id,
        resource_type="user", resource_id=current_user.id, status_code="success",
        details=f"Volunteer {current_user.name} upgraded account to email {email_clean}"
    )

    return current_user


