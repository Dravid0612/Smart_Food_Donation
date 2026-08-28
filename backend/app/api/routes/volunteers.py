from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.models import User, VolunteerAssignment, FoodDonation, Notification, DonationHistory, NGO
from app.schemas.schemas import (
    UserResponse, VolunteerAssignmentResponse, VolunteerProfileUpdate,
    VerifyOtpRequest, VerifyQRRequest, DonationFailureRequest,
    VolunteerRecommendationResponse, VolunteerLocationUpdateRequest, RescueTrackingResponse
)
from app.core.dependencies import get_current_user, require_role
from app.services.security_service import log_audit_event, validate_donation_transition
from app.services.recommendation_service import recommend_volunteers
from app.services.notification_service import create_notification, create_event_notification
from app.services.otp_service import generate_pickup_otp, send_pickup_otp_sms
from app.services.live_tracking_service import live_tracking_service

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

    volunteer = db.query(User).filter(User.id == volunteer_id, User.role == "volunteer").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer user not found.")

    # ── Capacity Safeguard: Validate volunteer carrying capacity ───────────
    vol_cap = volunteer.carrying_capacity or 50
    if donation.quantity > vol_cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Donation quantity ({donation.quantity} {donation.quantity_unit}) exceeds volunteer carrying capacity ({vol_cap} meals for vehicle '{volunteer.vehicle_type or 'bike'}'). Please assign a volunteer with adequate vehicle capacity."
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
        assignment.status = "assigned"

    donation.assigned_volunteer_id = volunteer.id
    donation.status = "volunteer_assigned"

    notification = Notification(
        user_id=volunteer.id,
        title="New Pickup Assignment",
        message=f"You have been assigned to pick up '{donation.food_name}' at {donation.pickup_address}.",
        type="assignment",
        related_donation_id=donation.id
    )
    db.add(notification)

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
    donation = db.query(FoodDonation).filter(FoodDonation.id == verify_in.donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # ── EARLY: OTP replay protection (checked before assignment lookup) ────────
    # Must run first: if OTP was already consumed, always 409 regardless of assignment state.
    if donation.otp_used_at is not None:
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

    from app.services.otp_service import verify_pickup_otp
    from app.models.models import PickupOtpRecord

    active_otp_record = db.query(PickupOtpRecord).filter(
        PickupOtpRecord.donation_id == donation.id,
        PickupOtpRecord.purpose == "PICKUP_VERIFICATION_OTP",
        PickupOtpRecord.is_active == True,
    ).first()

    if active_otp_record:
        verify_pickup_otp(db, donation, verify_in.otp.strip(), current_user)
    else:
        # ── 3. Legacy OTP expiry check ────────────────────────────────────
        if donation.otp_expiry:
            otp_expiry = donation.otp_expiry
            if otp_expiry.tzinfo is None:
                otp_expiry = otp_expiry.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > otp_expiry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP has expired. Please contact the donor for a new verification code."
                )

        # ── 4. Legacy OTP correctness check ─────────────────────────────────
        if not donation.verification_otp or donation.verification_otp.strip() != verify_in.otp.strip():
            log_audit_event(db, action="otp_failed", user_id=current_user.id,
                            resource_type="donation", resource_id=donation.id, status_code="failed")
            raise HTTPException(status_code=400, detail="Invalid OTP code. Please ask the donor for the correct code.")

    # ── All checks passed — consume OTP (replay protection) and update state ──
    now = datetime.now(timezone.utc)
    donation.otp_used_at = now  # Mark as consumed — prevents replay

    if not assignment:
        assignment = VolunteerAssignment(
            donation_id=donation.id,
            volunteer_id=current_user.id,
            status="collected"
        )
        db.add(assignment)

    assignment.collected_at = now
    assignment.status = "collected"

    donation.status = "collected"
    donation.assigned_volunteer_id = current_user.id

    db.add(DonationHistory(
        donation_id=donation.id,
        old_status="volunteer_assigned",
        new_status="collected",
        changed_by=current_user.id,
        remarks=f"Pickup verified securely with OTP by volunteer {current_user.name}"
    ))

    db.add(Notification(
        user_id=donation.donor_id,
        title="Food collected",
        message="Your donated food has been collected and is on its way to the NGO.",
        type="food_collected",
        related_donation_id=donation.id
    ))

    db.commit()
    db.refresh(assignment)

    log_audit_event(db, action="otp_verified", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success",
                    details=f"OTP pickup verified for donation {donation.id}")

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

    assignment.collected_at = now
    assignment.status = "collected"

    donation.status = "collected"
    donation.assigned_volunteer_id = current_user.id

    db.add(DonationHistory(
        donation_id=donation.id,
        old_status="volunteer_assigned",
        new_status="collected",
        changed_by=current_user.id,
        remarks=f"Pickup verified via QR Code scan by volunteer {current_user.name}"
    ))

    db.add(Notification(
        user_id=donation.donor_id,
        title="Food Handover Verified (QR)",
        message=f"Volunteer {current_user.name} scanned the QR code and collected '{donation.food_name}'.",
        type="info",
        related_donation_id=donation.id
    ))

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

    donation.status = status_name
    donation.failure_reason = f"{failure_in.reason}: {failure_in.remarks or ''}".strip()

    if assignment:
        assignment.status = "failed"
        assignment.failure_reason = donation.failure_reason

    # Adjust volunteer metrics
    current_user.failed_deliveries = (current_user.failed_deliveries or 0) + 1
    total = (current_user.completed_deliveries or 0) + current_user.failed_deliveries
    current_user.reliability_score = round(((current_user.completed_deliveries or 0) / float(total)) * 100, 1)

    # Log history
    db.add(DonationHistory(
        donation_id=donation.id,
        old_status="in_progress",
        new_status=status_name,
        changed_by=current_user.id,
        remarks=f"Task failure reported: {donation.failure_reason}"
    ))

    # Alert Donor & NGO
    db.add(Notification(
        user_id=donation.donor_id,
        title=f"Delivery Alert: {status_name.replace('_', ' ').title()}",
        message=f"Issue reported on '{donation.food_name}': {donation.failure_reason}",
        type="alert",
        related_donation_id=donation.id
    ))

    db.commit()
    if assignment:
        db.refresh(assignment)
        return assignment
    
    return VolunteerAssignmentResponse(
        id=0,
        donation_id=donation.id,
        volunteer_id=current_user.id,
        assigned_at=datetime.now(timezone.utc),
        status="failed",
        failure_reason=donation.failure_reason
    )

@router.put("/assignments/{assignment_id}", response_model=VolunteerAssignmentResponse)
def update_volunteer_assignment_status(
    assignment_id: int,
    status_update: str, # accepted, collected, delivered, cancelled
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "ngo", "admin"]))
):
    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    # Ownership check: volunteer can only update their own assignment
    if current_user.role == "volunteer" and assignment.volunteer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this assignment."
        )

    now = datetime.now(timezone.utc)
    assignment.status = status_update.lower()

    if status_update.lower() == "accepted":
        assignment.accepted_at = now
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            donation.status = "volunteer_assigned"
            donation.assigned_volunteer_id = assignment.volunteer_id
    elif status_update.lower() in ["en_route", "pickup_en_route"]:
        assignment.status = "en_route"
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            donation.status = "pickup_en_route"
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
    elif status_update.lower() in ["arrived", "arrived_at_donor"]:
        assignment.status = "arrived"
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            donation.status = "arrived_at_donor"
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
    elif status_update.lower() in ["in_transit", "transit"]:
        assignment.status = "in_transit"
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            donation.status = "in_transit"
    elif status_update.lower() == "collected":
        assignment.collected_at = now
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            donation.status = "collected"
            db.add(Notification(
                user_id=donation.donor_id,
                title="Food collected",
                message="Your donated food has been collected and is on its way to the NGO.",
                type="food_collected",
                related_donation_id=donation.id
            ))
    elif status_update.lower() == "delivered":
        assignment.delivered_at = now
        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if donation:
            old_st = donation.status
            donation.status = "delivered"
            db.add(DonationHistory(
                donation_id=donation.id,
                old_status=old_st,
                new_status="delivered",
                changed_by=current_user.id,
                remarks=f"Delivered to NGO by volunteer {current_user.name}"
            ))
            db.add(Notification(
                user_id=donation.donor_id,
                title="Food delivered",
                message="Your donation has reached the receiving NGO.",
                type="food_delivered",
                related_donation_id=donation.id
            ))

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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin"]))
):
    """Signals that volunteer has physically arrived at donor location, triggering donor arrival notification."""
    return update_volunteer_assignment_status(assignment_id, "arrived", db, current_user)

@router.get("/assignments/{assignment_id}", response_model=VolunteerAssignmentResponse)
def get_volunteer_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    if current_user.role == "volunteer" and assignment.volunteer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to accept this assignment.")

    donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
    if donation:
        donation.status = "volunteer_assigned"
        donation.assigned_volunteer_id = assignment.volunteer_id

    now = datetime.now(timezone.utc)
    assignment.status = "accepted"
    assignment.accepted_at = now

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
            donation.status = "accepted"

    assignment.status = "cancelled"
    assignment.failure_reason = reason

    # Fallback Matching: Alert next available volunteer
    fallback_notified = False
    if donation:
        matches = recommend_volunteers(db, donation)
        for m in matches:
            if m["volunteer_id"] != assignment.volunteer_id:
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
        "fallback_notified": fallback_notified
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


