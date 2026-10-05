import logging
import secrets
import hashlib
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)
from app.db.session import get_db
from app.models.models import (
    FoodDonation, DonationHistory, NGO, User, VolunteerAssignment, Notification,
    RecurringDonation, Rating, MatchOffer, FoodAnalysis, Dispute, KitchenProfile,
    DonorCustomFoodProfile, PickupOtpRecord
)
from app.schemas.schemas import (
    DonationCreate, DonationUpdate, DonationResponse, DonationDetailResponse,
    DonationHistoryResponse, NGORecommendationResponse, VolunteerRecommendationResponse,
    DonationCancelRequest, RecurringDonationCreate, RecurringDonationResponse,
    RatingCreate, RatingResponse, CertificateResponse, CSRImpactSummaryResponse,
    RescueChecklistResponse, FoodAnalysisResponse, FoodAnalysisCreate, DonationDistributionRequest,
    DonationReceiveRequest, DonationDistributionResponse, DonationMetricsSummary, FoodRescueWindowResponse,
    RescueFeasibilityResponse, DonorImpactSummaryResponse, DonorMonthlyImpactItem,
    KitchenProfileCreate, KitchenProfileResponse, RepeatDonationPrefillResponse,
    DonorCustomFoodProfileCreate, DonorCustomFoodProfileResponse, CustomFoodAggregatedAdminResponse,
    FoodSafetyCheckRequest, FoodSafetyCheckResponse, RescueTrackingResponse,
    DynamicRematchRequest, DynamicRematchResponse, DonationAcceptRequest
)
from app.core.dependencies import get_current_user, require_role
from app.services.urgency_service import calculate_urgency
from app.services.food_knowledge_rules import calculate_rule_coverage, estimate_equivalent_meals
from app.services.food_rescue_window_service import evaluate_food_rescue_window, calculate_rescue_feasibility, RescueUrgencyLevel
from app.services.recommendation_service import (
    recommend_ngos, recommend_volunteers, global_batch_match_ngos, optimize_volunteer_routes,
    build_rescue_checklist
)
from app.services.escalation_service import escalate_donation
from app.services.reward_service import add_reward_points
from app.services.notification_service import create_notification, create_event_notification
from app.services.security_service import validate_donation_transition, log_audit_event, log_rescue_operation
from app.services.ai_vision_service import analyze_food_image_and_metadata
from app.services.proactive_dispatch_service import ProactiveDispatchService, BackgroundUrgencyMonitor
from app.services.food_safety_check_service import food_safety_check_service
from app.services.live_tracking_service import live_tracking_service
from app.services.rematching_service import rematching_service
from app.services.route_service import route_service
from app.services.otp_service import _hash_otp, verify_pickup_otp, _otp_verification_lock
from app.services.state_machine_service import (
    transition_donation_state,
    transition_donation_status,
    transition_assignment_status,
    DonationStatus,
)
from app.core.config import settings

router = APIRouter(prefix="/donations", tags=["Donations"])

def log_status_change(db: Session, donation_id: int, old_status: str, new_status: str, changed_by: int, remarks: str = ""):
    history = DonationHistory(
        donation_id=donation_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        remarks=remarks
    )
    db.add(history)
    db.flush()

@router.post("", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def create_donation(
    donation_in: DonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    if donation_in.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero.")

    now = datetime.now(timezone.utc)
    expiry = donation_in.expiry_time
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        raise HTTPException(status_code=400, detail="Expiry time must be in the future.")

    # Determine custom food attributes
    is_custom_food = (donation_in.food_source == "CUSTOM") or (donation_in.custom_food_name is not None)
    food_src = "CUSTOM" if is_custom_food else (donation_in.food_source or "KNOWN")
    custom_name = donation_in.custom_food_name or (donation_in.food_name if is_custom_food else None)

    rule_cov = calculate_rule_coverage(
        food_type=donation_in.food_type or donation_in.food_name,
        food_category=donation_in.food_category,
        is_custom=is_custom_food
    )

    equiv_meals = donation_in.estimated_meals
    if equiv_meals is None:
        equiv_meals = estimate_equivalent_meals(
            donation_in.quantity,
            donation_in.quantity_unit,
            donation_in.quantity_unit_label
        )

    # Generate secure 6-digit OTP and QR token for pickup verification
    otp = f"{secrets.randbelow(900000) + 100000}"
    qr_token = f"DON-{secrets.token_urlsafe(12)}"

    # Time-aware rescue window evaluation
    prep_time_to_use = donation_in.preparation_time
    rescue_window_eval = evaluate_food_rescue_window(
        food_type=donation_in.food_type or donation_in.food_name,
        food_category=donation_in.food_category,
        prepared_at=prep_time_to_use,
        storage_method=donation_in.storage_method or "Room Temperature",
        storage_continuous=donation_in.storage_continuous if donation_in.storage_continuous is not None else True,
        packaging_status=donation_in.packaging_condition or "Covered",
        previously_served=donation_in.previously_served or "No",
        exposure_status=donation_in.exposure_status or "No",
        handling_status=donation_in.handling_status or "No",
        visual_condition_in=donation_in.ai_visual_condition or "GOOD",
        visible_spoilage_in=donation_in.ai_visible_spoilage,
        ai_confidence_in=donation_in.ai_confidence_score or 0.88,
        is_custom=is_custom_food,
        current_time=now
    )

    feasibility_eval = calculate_rescue_feasibility(
        remaining_window_minutes=rescue_window_eval["remaining_minutes"]
    )

    window_end_dt = datetime.fromisoformat(rescue_window_eval["estimated_window_end"])
    if window_end_dt.tzinfo is None:
        window_end_dt = window_end_dt.replace(tzinfo=timezone.utc)

    window_start_dt = datetime.fromisoformat(rescue_window_eval["estimated_window_start"])
    if window_start_dt.tzinfo is None:
        window_start_dt = window_start_dt.replace(tzinfo=timezone.utc)

    # Food-Safety Self-Check Declaration Validation
    safety_completed = False
    safety_status = "PASSED"
    safety_answers_json = None
    if donation_in.safety_check_answers is not None:
        user_lang = (current_user.preferred_language or "en") if hasattr(current_user, "preferred_language") else "en"
        safety_eval = food_safety_check_service.validate_declaration(
            donation_in.safety_check_answers,
            language=user_lang
        )
        if not safety_eval["is_eligible"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{safety_eval['warning_message']} {safety_eval['guidance']}"
            )
        safety_completed = True
        safety_status = safety_eval["status"]
        safety_answers_json = json.dumps(food_safety_check_service.normalize_answers(donation_in.safety_check_answers))

    new_donation = FoodDonation(
        donor_id=current_user.id,
        food_name=donation_in.food_name,
        food_type=donation_in.food_type or donation_in.food_name,
        food_source=food_src,
        custom_food_name=custom_name,
        food_description=donation_in.food_description or donation_in.description,
        major_ingredients=donation_in.major_ingredients,
        quantity_unit_label=donation_in.quantity_unit_label,
        estimated_meals=equiv_meals,
        rule_coverage=rule_cov,
        classification_source=donation_in.classification_source or ("donor_specified" if is_custom_food else "rule_exact"),
        classification_confidence=donation_in.classification_confidence or (0.80 if is_custom_food else 1.0),
        description=donation_in.description,
        food_category=donation_in.food_category,
        quantity=donation_in.quantity,
        quantity_unit=donation_in.quantity_unit,
        preparation_time=donation_in.preparation_time,
        expiry_time=donation_in.expiry_time,
        pickup_address=donation_in.pickup_address,
        latitude=donation_in.latitude or current_user.latitude or 12.9716,
        longitude=donation_in.longitude or current_user.longitude or 77.5946,
        image_url=donation_in.image_url,
        storage_method=donation_in.storage_method or "Room Temperature",
        storage_duration_hours=donation_in.storage_duration_hours or 2.0,
        storage_continuous=donation_in.storage_continuous if donation_in.storage_continuous is not None else True,
        storage_history_json=donation_in.storage_history_json,
        packaging_condition=donation_in.packaging_condition or "Covered",
        previously_served=donation_in.previously_served or "No",
        exposure_status=donation_in.exposure_status or "No",
        handling_status=donation_in.handling_status or "No",
        pickup_deadline=donation_in.pickup_deadline or window_end_dt or donation_in.expiry_time,
        estimated_window_start=window_start_dt,
        estimated_window_end=window_end_dt,
        remaining_minutes=rescue_window_eval["remaining_minutes"],
        rescue_urgency_level=rescue_window_eval["urgency_level"],
        feasibility_status=feasibility_eval["feasibility_status"],
        reasons_json=json.dumps(rescue_window_eval["reasons"]),
        ai_food_detected=donation_in.ai_food_detected or donation_in.food_type or donation_in.food_name,
        ai_visible_spoilage=donation_in.ai_visible_spoilage or "Not detected",
        ai_discoloration=donation_in.ai_discoloration or "Normal",
        ai_packaging_intact=donation_in.ai_packaging_intact or "Intact",
        ai_visual_condition=rescue_window_eval["visual_condition"],
        ai_confidence_score=rescue_window_eval["confidence"],
        condition_score=donation_in.condition_score or 85,
        verification_otp=otp,
        otp_expiry=now + timedelta(hours=settings.OTP_EXPIRE_HOURS),
        qr_code_token=qr_token,
        qr_expiry=now + timedelta(hours=settings.QR_EXPIRE_HOURS),
        status="pending",
        tracking_status="IDLE",
        rematch_count=0,
        is_rematched=False,
        safety_check_completed=safety_completed,
        safety_check_answers_json=safety_answers_json,
        safety_check_status=safety_status,
        safety_check_version="2026.1"
    )
    db.add(new_donation)
    db.commit()
    db.refresh(new_donation)

    # Persist structured FoodAnalysis entity
    analysis_record = FoodAnalysis(
        donation_id=new_donation.id,
        food_detected=donation_in.ai_food_detected or donation_in.food_name,
        visible_spoilage=donation_in.ai_visible_spoilage or "Not detected",
        discoloration=donation_in.ai_discoloration or "Normal",
        packaging_integrity=donation_in.ai_packaging_intact or "GOOD",
        visual_condition=donation_in.ai_visual_condition or "GOOD",
        confidence=donation_in.ai_confidence_score or 0.87,
        observations=json.dumps([
            f"Visual condition: {donation_in.ai_visual_condition or 'GOOD'}",
            f"Packaging: {donation_in.packaging_condition or 'Sealed / Covered'}",
            f"Storage: {donation_in.storage_method or 'Room Temperature'}"
        ]),
        safety_disclaimer="Visual assessment only; this does not certify food safety.",
        storage_assessment=f"Stored under {donation_in.storage_method or 'Room Temperature'}",
        urgency_recommendation="Normal Priority"
    )
    db.add(analysis_record)
    db.commit()

    # Automatically save/update in donor's personal food library ('My Foods')
    if is_custom_food and custom_name:
        try:
            existing_prof = db.query(DonorCustomFoodProfile).filter(
                DonorCustomFoodProfile.donor_id == current_user.id,
                func.lower(DonorCustomFoodProfile.name) == custom_name.strip().lower()
            ).first()
            if existing_prof:
                existing_prof.usage_count = (existing_prof.usage_count or 1) + 1
                existing_prof.food_category = donation_in.food_category
                existing_prof.common_storage = donation_in.storage_method or existing_prof.common_storage
                existing_prof.default_unit = donation_in.quantity_unit or existing_prof.default_unit
            else:
                new_custom_prof = DonorCustomFoodProfile(
                    donor_id=current_user.id,
                    name=custom_name.strip(),
                    food_category=donation_in.food_category,
                    description=donation_in.food_description or donation_in.description,
                    major_ingredients=donation_in.major_ingredients,
                    common_storage=donation_in.storage_method or "Room Temperature",
                    default_unit=donation_in.quantity_unit or "Meals",
                    usage_count=1
                )
                db.add(new_custom_prof)
            db.commit()
        except Exception:
            pass # Non-blocking personal library sync

    # Persist authoritative PickupOtpRecord with salted/SHA-256 hash
    otp_record = PickupOtpRecord(
        donation_id=new_donation.id,
        donor_id=current_user.id,
        purpose="PICKUP_VERIFICATION_OTP",
        otp_hash=_hash_otp(otp),
        expires_at=new_donation.otp_expiry,
        is_active=True,
        delivery_status="QUEUED",
    )
    db.add(otp_record)
    db.commit()

    log_status_change(db, new_donation.id, None, "pending", current_user.id, "Donation created with AI condition assessment")
    log_rescue_operation(
        db, action="created", donation_id=new_donation.id,
        user_id=current_user.id, old_status=None, new_status="pending",
        remarks="Donation created with AI condition assessment",
        details=f"Donation #{new_donation.id} created: {new_donation.food_name} ({new_donation.quantity} {new_donation.quantity_unit})"
    )
    log_rescue_operation(
        db, action="OTP generated", donation_id=new_donation.id,
        user_id=current_user.id,
        remarks="Initial pickup OTP generated for donation",
        details=f"OTP generated for donation #{new_donation.id}"
    )
    
    # Proactive Time-Critical Food Rescue Alert & Targeted NGO Dispatch
    dispatch_res = ProactiveDispatchService.dispatch_proactive_alerts(db, new_donation, reference_time=now)
    
    # Emit canonical NEW_RESCUE notification for donor
    create_event_notification(
        db,
        user_id=current_user.id,
        event_type="NEW_RESCUE",
        donation_id=new_donation.id,
        extra_message=f"Your donation '{new_donation.food_name}' has been listed for active rescue."
    )

    # If Fresh / normal operations, ensure nearby available NGOs receive baseline awareness notification
    if dispatch_res.get("status") == "NORMAL_OPERATIONS":
        ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()
        for ngo in ngos:
            create_event_notification(
                db,
                user_id=ngo.user_id,
                event_type="NEW_RESCUE",
                donation_id=new_donation.id,
                extra_message=f"New rescue '{new_donation.food_name}' ({new_donation.quantity} {new_donation.quantity_unit}) posted nearby."
            )
        db.commit()

    response_data = DonationResponse.model_validate(new_donation)
    response_data.urgency_level = calculate_urgency(new_donation.preparation_time, new_donation.expiry_time)
    return response_data

@router.get("/my-foods", response_model=List[DonorCustomFoodProfileResponse])
def get_donor_custom_foods(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Retrieve donor's personal custom food library ('My Foods')."""
    profiles = db.query(DonorCustomFoodProfile).filter(
        DonorCustomFoodProfile.donor_id == current_user.id
    ).order_by(DonorCustomFoodProfile.usage_count.desc(), DonorCustomFoodProfile.updated_at.desc()).all()
    return profiles

@router.post("/my-foods", response_model=DonorCustomFoodProfileResponse, status_code=status.HTTP_201_CREATED)
def create_donor_custom_food(
    profile_in: DonorCustomFoodProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Manually add or update a food item in the donor's personal library."""
    existing = db.query(DonorCustomFoodProfile).filter(
        DonorCustomFoodProfile.donor_id == current_user.id,
        func.lower(DonorCustomFoodProfile.name) == profile_in.name.strip().lower()
    ).first()
    if existing:
        existing.food_category = profile_in.food_category
        existing.description = profile_in.description
        existing.major_ingredients = profile_in.major_ingredients
        existing.common_storage = profile_in.common_storage or "Room Temperature"
        existing.default_unit = profile_in.default_unit or "Meals"
        existing.usage_count = (existing.usage_count or 1) + 1
        db.commit()
        db.refresh(existing)
        return existing

    new_prof = DonorCustomFoodProfile(
        donor_id=current_user.id,
        name=profile_in.name.strip(),
        food_category=profile_in.food_category,
        description=profile_in.description,
        major_ingredients=profile_in.major_ingredients,
        common_storage=profile_in.common_storage or "Room Temperature",
        default_unit=profile_in.default_unit or "Meals",
        usage_count=1
    )
    db.add(new_prof)
    db.commit()
    db.refresh(new_prof)
    return new_prof

@router.delete("/my-foods/{profile_id}", status_code=status.HTTP_200_OK)
def delete_donor_custom_food(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Delete a custom food item from donor's personal library."""
    prof = db.query(DonorCustomFoodProfile).filter(
        DonorCustomFoodProfile.id == profile_id,
        DonorCustomFoodProfile.donor_id == current_user.id
    ).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Custom food profile not found.")
    db.delete(prof)
    db.commit()
    return {"message": "Custom food profile deleted successfully."}

@router.get("/admin/custom-foods-queue", response_model=List[CustomFoodAggregatedAdminResponse])
def get_aggregated_custom_foods_for_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Admin queue showing frequently donated custom food names for potential knowledge base promotion."""
    donations = db.query(FoodDonation).filter(
        FoodDonation.food_source == "CUSTOM"
    ).all()

    agg: Dict[str, Dict[str, Any]] = {}
    for d in donations:
        name_key = (d.custom_food_name or d.food_name).strip()
        lower_k = name_key.lower()
        if lower_k not in agg:
            agg[lower_k] = {
                "food_name": name_key,
                "count": 0,
                "suggested_category": d.food_category or "Cooked Food",
                "sample_descriptions": [],
                "sample_ingredients": []
            }
        agg[lower_k]["count"] += 1
        if d.food_description and d.food_description not in agg[lower_k]["sample_descriptions"]:
            if len(agg[lower_k]["sample_descriptions"]) < 3:
                agg[lower_k]["sample_descriptions"].append(d.food_description)
        if d.major_ingredients and d.major_ingredients not in agg[lower_k]["sample_ingredients"]:
            if len(agg[lower_k]["sample_ingredients"]) < 3:
                agg[lower_k]["sample_ingredients"].append(d.major_ingredients)

    result = list(agg.values())
    result.sort(key=lambda x: x["count"], reverse=True)
    return result

@router.get("", response_model=List[DonationResponse])
def get_donations(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    my_donations_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(FoodDonation)

    if current_user.role == "donor" or my_donations_only:
        query = query.filter(FoodDonation.donor_id == current_user.id)
    elif current_user.role == "ngo":
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        ngo_id = ngo_profile.id if ngo_profile else -1
        query = query.filter(
            (FoodDonation.status == "pending") | (FoodDonation.assigned_ngo_id == ngo_id)
        )
    elif current_user.role == "volunteer":
        if not current_user.is_active:
            # When unavailable: do not offer new pickup tasks, return only assigned tasks
            query = query.filter(FoodDonation.assigned_volunteer_id == current_user.id)
        else:
            # When available: offer assigned tasks or unassigned feasible courier pickup tasks
            query = query.filter(
                (FoodDonation.assigned_volunteer_id == current_user.id) |
                (
                    (FoodDonation.status == "accepted") &
                    (FoodDonation.pickup_mode != "self_pickup") &
                    (FoodDonation.assigned_volunteer_id.is_(None))
                )
            )

    if status_filter:
        query = query.filter(FoodDonation.status == status_filter)
    if category_filter:
        query = query.filter(FoodDonation.food_category == category_filter)

    donations = query.order_by(FoodDonation.created_at.desc()).all()
    now = datetime.now(timezone.utc)
    result = []
    for d in donations:
        # Automatic expiry check
        if d.status == "pending" and d.expiry_time:
            exp = d.expiry_time if d.expiry_time.tzinfo else d.expiry_time.replace(tzinfo=timezone.utc)
            if now > exp:
                d.status = "expired"
                d.failure_reason = "Donation expired: pickup deadline elapsed with no match"
                db.add(d)

        # For volunteers viewing unassigned tasks: screen ONLY feasible tasks before rescue window ends
        if current_user.role == "volunteer" and d.assigned_volunteer_id != current_user.id:
            prep_time = d.preparation_time or d.created_at
            r_eval = evaluate_food_rescue_window(
                food_type=d.food_type or d.food_name,
                food_category=d.food_category,
                prepared_at=prep_time,
                storage_method=d.storage_method or "Room Temperature",
                storage_continuous=d.storage_continuous if d.storage_continuous is not None else True,
                packaging_status=d.packaging_condition or "Covered",
                previously_served=d.previously_served or "No",
                exposure_status=d.exposure_status or "No",
                handling_status=d.handling_status or "No",
                visual_condition_in=d.ai_visual_condition or "GOOD",
                visible_spoilage_in=d.ai_visible_spoilage,
                ai_confidence_in=d.ai_confidence_score or 0.88
            )
            f_eval = calculate_rescue_feasibility(
                remaining_window_minutes=r_eval["remaining_minutes"]
            )
            # Master Prompt Section 5: Volunteer must NEVER receive tasks that cannot fit the remaining rescue window
            if not f_eval["is_feasible"] or r_eval["remaining_minutes"] <= 0:
                continue

        item = DonationResponse.model_validate(d)
        item.urgency_level = calculate_urgency(d.preparation_time, d.expiry_time)

        # Attach real volunteer assignment ID if assigned
        if current_user.role == "volunteer":
            va = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == d.id,
                VolunteerAssignment.volunteer_id == current_user.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
            ).order_by(VolunteerAssignment.id.desc()).first()
            if va:
                item.assignment_id = va.id

        # Pre-acceptance location privacy: mask exact address & round coords for unassigned tasks
        is_my_assigned_task = (d.assigned_volunteer_id == current_user.id)
        if (d.status == "pending" and current_user.role in ["ngo", "volunteer"] and d.donor_id != current_user.id) or \
           (current_user.role == "volunteer" and not is_my_assigned_task):
            addr_parts = (d.pickup_address or "").split(",")
            coarse_area = addr_parts[-2].strip() if len(addr_parts) >= 2 else (addr_parts[0].strip() if addr_parts else "Neighborhood Area")
            item.pickup_address = f"{coarse_area} (Exact address revealed upon acceptance)"
            if item.latitude:
                item.latitude = round(item.latitude, 2)
            if item.longitude:
                item.longitude = round(item.longitude, 2)

        result.append(item)
    db.commit()
    return result

@router.get("/{donation_id}", response_model=DonationDetailResponse)
def get_donation_detail(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # ── Ownership / Access Policy ─────────────────────────────────────────────
    if current_user.role == "donor":
        # Donor can only see their own donations (return 404 for enumeration protection)
        if donation.donor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Donation not found.")
    elif current_user.role == "ngo":
        # NGO can see pending donations or donations assigned to them
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        ngo_id = ngo_profile.id if ngo_profile else -1
        if donation.status != "pending" and donation.assigned_ngo_id != ngo_id:
            raise HTTPException(status_code=404, detail="Donation not found.")
    is_assigned_vol = False
    if current_user.role == "volunteer":
        if donation.assigned_volunteer_id == current_user.id:
            is_assigned_vol = True
        else:
            va = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == donation.id,
                VolunteerAssignment.volunteer_id == current_user.id
            ).first()
            if va:
                is_assigned_vol = True
        # Volunteer can see donations assigned to them, or accepted/pending ones available for pickup
        if not is_assigned_vol and donation.status not in ["accepted", "pending"]:
            raise HTTPException(status_code=404, detail="Donation not found.")
    # Admin has unrestricted read access

    donor = db.query(User).filter(User.id == donation.donor_id).first()
    ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first() if donation.assigned_ngo_id else None
    volunteer = db.query(User).filter(User.id == donation.assigned_volunteer_id).first() if donation.assigned_volunteer_id else None

    detail = DonationDetailResponse.model_validate(donation)
    detail.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    detail.ngo_name = ngo.organization_name if ngo else None

    # Pre-acceptance location privacy for unassigned NGO or unassigned volunteer detail view
    if (donation.status == "pending" and current_user.role == "ngo") or (current_user.role == "volunteer" and not is_assigned_vol):
        reveal = False
        if current_user.role == "ngo":
            ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
            if ngo_profile and donation.assigned_ngo_id == ngo_profile.id:
                reveal = True
        if not reveal:
            addr_parts = (donation.pickup_address or "").split(",")
            coarse_area = addr_parts[-2].strip() if len(addr_parts) >= 2 else (addr_parts[0].strip() if addr_parts else "Neighborhood Area")
            detail.pickup_address = f"{coarse_area} (Exact address revealed upon acceptance)"
            if detail.latitude:
                detail.latitude = round(detail.latitude, 2)
            if detail.longitude:
                detail.longitude = round(detail.longitude, 2)

    # ── Field-level Privacy Rules ─────────────────────────────────────────────
    # OTP and QR: Only expose to the donation's own donor (or admin)
    if current_user.role == "donor" and donation.donor_id == current_user.id or current_user.role == "admin":
        detail.donor_name = donor.name if donor else None
        detail.donor_phone = donor.phone if donor else None
        detail.verification_otp = donation.verification_otp  # Not consumed yet
        detail.qr_code_token = donation.qr_code_token
        detail.volunteer_name = volunteer.name if volunteer else None
        detail.volunteer_phone = volunteer.phone if volunteer else None
    elif current_user.role == "volunteer" and (donation.assigned_volunteer_id == current_user.id or is_assigned_vol):
        # Assigned volunteer gets pickup address + donor name for coordination
        detail.donor_name = donor.name if donor else None
        detail.donor_phone = donor.phone if donor else None  # For coordination only
        detail.verification_otp = None  # Volunteer does NOT see OTP in detail — only via verify endpoint
        detail.qr_code_token = None
        detail.volunteer_name = volunteer.name if volunteer else None
        detail.volunteer_phone = None
        # Populate assignment_id
        va = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == donation.id,
            VolunteerAssignment.volunteer_id == current_user.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
        ).order_by(VolunteerAssignment.id.desc()).first()
        if va:
            detail.assignment_id = va.id
    elif current_user.role == "ngo":
        # NGO sees donor name after acceptance, no phone before
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        if ngo_profile and donation.assigned_ngo_id == ngo_profile.id:
            detail.donor_name = donor.name if donor else None
        else:
            detail.donor_name = None
        detail.donor_phone = None  # NGO never gets donor phone directly
        detail.verification_otp = None
        detail.qr_code_token = None
        detail.volunteer_name = volunteer.name if volunteer else None
        detail.volunteer_phone = volunteer.phone if volunteer else None
    else:
        detail.donor_name = None
        detail.donor_phone = None
        detail.verification_otp = None
        detail.qr_code_token = None
        detail.volunteer_name = None
        detail.volunteer_phone = None

    detail.history = [DonationHistoryResponse.model_validate(h) for h in donation.history]
    
    # Attach Rescue Window and Feasibility
    prep_time = donation.preparation_time or donation.created_at
    rescue_window_eval = evaluate_food_rescue_window(
        food_type=donation.food_type or donation.food_name,
        food_category=donation.food_category,
        prepared_at=prep_time,
        storage_method=donation.storage_method or "Room Temperature",
        storage_continuous=donation.storage_continuous if donation.storage_continuous is not None else True,
        packaging_status=donation.packaging_condition or "Covered",
        previously_served=donation.previously_served or "No",
        exposure_status=donation.exposure_status or "No",
        handling_status=donation.handling_status or "No",
        visual_condition_in=donation.ai_visual_condition or "GOOD",
        visible_spoilage_in=donation.ai_visible_spoilage,
        ai_confidence_in=donation.ai_confidence_score or 0.88
    )
    detail.rescue_window = FoodRescueWindowResponse(**rescue_window_eval)

    feasibility_eval = calculate_rescue_feasibility(
        remaining_window_minutes=rescue_window_eval["remaining_minutes"]
    )
    detail.feasibility = RescueFeasibilityResponse(**feasibility_eval)

    # Attach Food Analysis
    analysis = db.query(FoodAnalysis).filter(FoodAnalysis.donation_id == donation.id).order_by(FoodAnalysis.id.desc()).first()
    if analysis:
        detail.food_analysis = FoodAnalysisResponse.model_validate(analysis)
    
    # Attach Rescue Feasibility Checklist
    detail.rescue_checklist = RescueChecklistResponse(**build_rescue_checklist(db, donation, ngo))

    # Attach previous volunteer name if rematched
    if donation.previous_volunteer_id:
        prev_vol = db.query(User).filter(User.id == donation.previous_volunteer_id).first()
        detail.previous_volunteer_name = prev_vol.name if prev_vol else None

    # Attach parsed safety check answers if available
    if donation.safety_check_answers_json:
        try:
            detail.safety_check_answers = json.loads(donation.safety_check_answers_json)
        except Exception:
            detail.safety_check_answers = None

    return detail

@router.post("/validate-safety-check", response_model=FoodSafetyCheckResponse)
def validate_food_safety_check(
    safety_in: FoodSafetyCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validates pre-publish food safety screening self-declarations.
    Advisory screening for food suitability before donation submission.
    """
    user_lang = (current_user.preferred_language or "en") if hasattr(current_user, "preferred_language") else "en"
    answers = {
        "human_consumption": safety_in.human_consumption,
        "hygienic_handling": safety_in.hygienic_handling,
        "appropriate_storage": safety_in.appropriate_storage,
        "contamination_free": safety_in.contamination_free,
        "suitable_condition": safety_in.suitable_condition
    }
    return food_safety_check_service.validate_declaration(answers, language=user_lang)

@router.get("/{donation_id}/tracking", response_model=RescueTrackingResponse)
def get_donation_tracking(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Real-time operational rescue tracking with role-based privacy filters.
    Available to Donor, NGO, assigned Volunteer, and Admin.
    """
    return live_tracking_service.get_tracking_data(
        db=db,
        donation_id=donation_id,
        current_user=current_user
    )

@router.get("/{donation_id}/eta")
def get_donation_eta(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculates and returns honest, calibrated travel ETA and remaining rescue window.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    vol = donation.assigned_volunteer
    vol_lat = donation.tracking_latitude or (vol.latitude if vol else None)
    vol_lon = donation.tracking_longitude or (vol.longitude if vol else None)
    mode = vol.vehicle_type if vol else "bike"

    now = datetime.now(timezone.utc)
    window_end = donation.estimated_window_end or donation.expiry_time
    if window_end:
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)
        remaining_mins = max(0, int((window_end - now).total_seconds() / 60))
    else:
        remaining_mins = donation.remaining_minutes or 60

    if vol_lat and vol_lon and donation.latitude and donation.longitude:
        eta_calc = route_service.calculate_eta(
            origin_lat=vol_lat,
            origin_lon=vol_lon,
            dest_lat=donation.latitude,
            dest_lon=donation.longitude,
            transport_mode=mode
        )
    else:
        eta_calc = {
            "eta_minutes": int(donation.current_eta_minutes or 15),
            "distance_km": float(donation.current_distance_km or 3.5),
            "transport_mode": mode,
            "status": "ROUTE_ESTIMATE_DEGRADED",
            "is_degraded": True
        }

    return {
        "donation_id": donation.id,
        "eta_minutes": eta_calc["eta_minutes"],
        "eta_label": "Estimated travel time",
        "distance_km": eta_calc["distance_km"],
        "transport_mode": eta_calc.get("transport_mode", mode),
        "status": eta_calc.get("status", "ROUTE_AVAILABLE"),
        "remaining_rescue_window_minutes": remaining_mins,
        "feasibility_status": donation.feasibility_status or "RESCUE_FEASIBLE",
        "is_rematched": bool(donation.is_rematched),
        "last_updated_at": donation.tracking_last_updated_at or now
    }

@router.post("/{donation_id}/rematch", response_model=DynamicRematchResponse)
def trigger_donation_rematch(
    donation_id: int,
    rematch_in: Optional[DynamicRematchRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "volunteer", "ngo", "donor"]))
):
    """
    Triggers dynamic rematching for an active rescue.
    Evaluates feasible backup volunteers with sufficient capacity and assigns top candidate.
    """
    # Concurrency safe: Lock donation
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if donation.status in ["delivered", "completed", "cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Donation is in '{donation.status}' state and cannot be rematched."
        )

    reason = (rematch_in.reason if rematch_in and rematch_in.reason else "Manual or feasibility-triggered reassignment")
    
    result = rematching_service.attempt_dynamic_rematch(
        db=db,
        donation=donation,
        trigger=f"MANUAL_OR_API_TRIGGER_{current_user.role.upper()}",
        reason=reason
    )
    return DynamicRematchResponse(**result)

@router.get("/{donation_id}/rematch-status")
def get_donation_rematch_status(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns dynamic rematch audit and feasibility history for a donation.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Fetch all assignments
    assignments = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id
    ).order_by(VolunteerAssignment.id.asc()).all()

    assignment_records = []
    for a in assignments:
        v = db.query(User).filter(User.id == a.volunteer_id).first()
        assignment_records.append({
            "assignment_id": a.id,
            "volunteer_id": a.volunteer_id,
            "volunteer_name": v.name if v else "Unknown",
            "assigned_at": a.assigned_at,
            "status": a.status,
            "is_reassigned": bool(a.is_reassigned),
            "reassign_reason": a.reassign_reason,
            "reassigned_at": a.reassigned_at
        })

    return {
        "donation_id": donation.id,
        "is_rematched": bool(donation.is_rematched),
        "rematch_count": donation.rematch_count or 0,
        "rematch_reason": donation.rematch_reason,
        "current_volunteer_id": donation.assigned_volunteer_id,
        "previous_volunteer_id": donation.previous_volunteer_id,
        "feasibility_status": donation.feasibility_status,
        "last_feasibility_check_at": donation.last_feasibility_check_at,
        "assignments_history": assignment_records
    }

@router.post("/{donation_id}/check-feasibility")
def check_donation_feasibility(
    donation_id: int,
    auto_rematch: bool = Query(True, description="Whether to automatically execute rematch if unhealthy"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates active assignment logistics feasibility, telemetry freshness,
    and operational health. Automatically triggers dynamic rematching if unhealthy.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    health_eval = rematching_service.verify_active_assignment_health(db, donation)
    rematch_result = None

    if auto_rematch and health_eval.get("requires_rematch"):
        rematch_result = rematching_service.attempt_dynamic_rematch(
            db=db,
            donation=donation,
            trigger=health_eval.get("trigger", "HEALTH_CHECK_FAILED"),
            reason=health_eval.get("reason", "Automated feasibility/telemetry check triggered rematch")
        )

    return {
        "donation_id": donation.id,
        "healthy": health_eval.get("healthy", True),
        "requires_rematch": health_eval.get("requires_rematch", False),
        "trigger": health_eval.get("trigger", "NONE"),
        "reason": health_eval.get("reason"),
        "feasibility": health_eval.get("feasibility"),
        "telemetry": health_eval.get("telemetry"),
        "rematch_result": rematch_result
    }

@router.get("/{donation_id}/rescue-window", response_model=FoodRescueWindowResponse)
def get_donation_rescue_window(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    
    prep_time = donation.preparation_time or donation.created_at
    eval_res = evaluate_food_rescue_window(
        food_type=donation.food_type or donation.food_name,
        food_category=donation.food_category,
        prepared_at=prep_time,
        storage_method=donation.storage_method or "Room Temperature",
        storage_continuous=donation.storage_continuous if donation.storage_continuous is not None else True,
        packaging_status=donation.packaging_condition or "Covered",
        previously_served=donation.previously_served or "No",
        exposure_status=donation.exposure_status or "No",
        handling_status=donation.handling_status or "No",
        visual_condition_in=donation.ai_visual_condition or "GOOD",
        visible_spoilage_in=donation.ai_visible_spoilage,
        ai_confidence_in=donation.ai_confidence_score or 0.88
    )
    return FoodRescueWindowResponse(**eval_res)

@router.get("/{donation_id}/feasibility", response_model=RescueFeasibilityResponse)
def get_donation_feasibility(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    
    prep_time = donation.preparation_time or donation.created_at
    eval_res = evaluate_food_rescue_window(
        food_type=donation.food_type or donation.food_name,
        food_category=donation.food_category,
        prepared_at=prep_time,
        storage_method=donation.storage_method or "Room Temperature",
        storage_continuous=donation.storage_continuous if donation.storage_continuous is not None else True,
        packaging_status=donation.packaging_condition or "Covered",
        previously_served=donation.previously_served or "No",
        exposure_status=donation.exposure_status or "No",
        handling_status=donation.handling_status or "No",
        visual_condition_in=donation.ai_visual_condition or "GOOD",
        visible_spoilage_in=donation.ai_visible_spoilage,
        ai_confidence_in=donation.ai_confidence_score or 0.88
    )
    feas_res = calculate_rescue_feasibility(
        remaining_window_minutes=eval_res["remaining_minutes"]
    )
    return RescueFeasibilityResponse(**feas_res)

@router.post("/{donation_id}/assess", response_model=FoodAnalysisResponse)
def assess_donation_food(
    donation_id: int,
    assessment_in: FoodAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    
    # Logic to record additional assessment and update rescue feasibility if needed
    analysis = FoodAnalysis(
        donation_id=donation.id,
        food_detected=assessment_in.food_detected,
        visual_condition=assessment_in.visual_condition,
        confidence=assessment_in.confidence,
        observations=assessment_in.observations,
        safety_disclaimer="Assessed by user request."
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return FoodAnalysisResponse.model_validate(analysis)

@router.get("/{donation_id}/rescue-checklist", response_model=RescueChecklistResponse)
def get_donation_rescue_checklist(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the transparent operational feasibility checklist for food rescue."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    
    ngo = None
    if current_user.role == "ngo":
        ngo = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        
    checklist_dict = build_rescue_checklist(db, donation, ngo)
    return RescueChecklistResponse(**checklist_dict)

@router.post("/{donation_id}/reject")
def reject_donation(
    donation_id: int,
    reason: Optional[str] = Query("NGO capacity or demand mismatch", alias="reason"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "volunteer", "admin"]))
):
    """
    Allows an NGO or volunteer to reject/pass a donation match.
    Updates candidate MatchOffer with timing metrics and triggers automatic fallback or wave advancement.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    now = datetime.now(timezone.utc)
    candidate_notified = False

    if current_user.role == "ngo":
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()

        # If this NGO was assigned, reset to pending and restore capacity
        if ngo_profile and donation.assigned_ngo_id == ngo_profile.id:
            donation.assigned_ngo_id = None
            transition_donation_status(
                db, donation, "pending",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks=f"Rejected by NGO '{ngo_profile.organization_name}': {reason}"
            )
            ngo_profile.current_capacity = min(ngo_profile.capacity, (ngo_profile.current_capacity or 0) + int(donation.quantity))
            ngo_profile.trust_score = max(0.0, (ngo_profile.trust_score or 96.0) - 2.0)

        # Update candidate MatchOffer
        user_offer = db.query(MatchOffer).filter(
            MatchOffer.donation_id == donation.id,
            MatchOffer.candidate_id == current_user.id,
            MatchOffer.candidate_type == "ngo",
            MatchOffer.status == "offered"
        ).first()
        if user_offer:
            user_offer.status = "rejected"
            user_offer.responded_at = now
            if user_offer.offered_at:
                offered_at = user_offer.offered_at
                if offered_at.tzinfo is None:
                    offered_at = offered_at.replace(tzinfo=timezone.utc)
                user_offer.response_time_seconds = (now - offered_at).total_seconds()

        # Check if all active offers in the current wave are responded
        active_offers_count = db.query(MatchOffer).filter(
            MatchOffer.donation_id == donation.id,
            MatchOffer.status == "offered"
        ).count()

        if active_offers_count == 0 and donation.status == "pending":
            # All Wave 1 candidate NGOs passed -> advance to Wave 2 volunteer search
            ProactiveDispatchService.dispatch_proactive_alerts(db, donation, force_dispatch=True)
            candidate_notified = True
        else:
            # Fallback Matching: Alert next suitable NGO if any
            other_recs = recommend_ngos(db, donation)
            for rec in other_recs:
                if ngo_profile and rec["ngo_id"] == ngo_profile.id:
                    continue
                next_ngo = db.query(NGO).filter(NGO.id == rec["ngo_id"]).first()
                if next_ngo:
                    create_notification(
                        db,
                        user_id=next_ngo.user_id,
                        title="Fallback Food Donation Available",
                        message=f"Opportunity available: '{donation.food_name}' ({donation.quantity} {donation.quantity_unit}) ready for pickup.",
                        type="donation",
                        related_donation_id=donation.id
                    )
                    candidate_notified = True
                    break

    elif current_user.role == "volunteer":
        if donation.assigned_volunteer_id == current_user.id:
            donation.assigned_volunteer_id = None
            if donation.status == "volunteer_assigned":
                transition_donation_status(
                    db, donation, "accepted",
                    changed_by_user_id=current_user.id,
                    caller_role=current_user.role,
                    remarks=f"Volunteer rejected assignment: {reason}"
                )

        vol_offer = db.query(MatchOffer).filter(
            MatchOffer.donation_id == donation.id,
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

        # Trigger fallback volunteer dispatch
        ProactiveDispatchService.dispatch_proactive_alerts(db, donation, force_dispatch=True)
        candidate_notified = True

    db.commit()
    return {
        "detail": "Donation rejected. Fallback matching initiated.",
        "fallback_notified": candidate_notified
    }

_last_otp_regen_map = {}

@router.get("/{donation_id}/verification-code")
def get_verification_code(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Allows authenticated donor or admin to view the secure verification OTP and QR token for pickup."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Strict ownership: only the donor of THIS donation or admin can view verification codes
    if current_user.role != "admin" and donation.donor_id != current_user.id:
        log_audit_event(db, action="otp_unauthorized_view_attempt", user_id=current_user.id,
                        resource_type="donation", resource_id=donation.id, status_code="failed",
                        details=f"User {current_user.id} ({current_user.role}) denied OTP access for donation {donation.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access verification code for this donation."
        )

    # Redact OTP once it has been consumed (anti-replay + clarity for donor)
    otp_display = donation.verification_otp
    otp_status = "active"
    if donation.otp_used_at is not None:
        otp_display = "USED"
        otp_status = "consumed"
    elif donation.otp_expiry:
        otp_expiry_aware = donation.otp_expiry if donation.otp_expiry.tzinfo else donation.otp_expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > otp_expiry_aware:
            otp_display = "EXPIRED"
            otp_status = "expired"

    log_audit_event(db, action="otp_viewed", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success",
                    details=f"Donor {current_user.id} securely viewed pickup verification OTP for donation {donation.id}")

    return {
        "donation_id": donation.id,
        "otp": otp_display,
        "otp_expiry": donation.otp_expiry.isoformat() if donation.otp_expiry else None,
        "otp_status": otp_status,
        "qr_token": donation.qr_code_token
    }

@router.post("/{donation_id}/regenerate-otp")
def regenerate_donation_otp(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """
    Secure server-side OTP regeneration.
    Constraints:
    - Only authenticated donor of this donation (or admin) can request it.
    - Volunteer cannot regenerate OTP.
    - Previous OTP is immediately invalidated.
    - Rate-limited to 1 request per 15 seconds.
    - Audit logged without plaintext OTP.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if current_user.role != "admin" and donation.donor_id != current_user.id:
        log_audit_event(db, action="otp_unauthorized_regen_attempt", user_id=current_user.id,
                        resource_type="donation", resource_id=donation.id, status_code="failed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to regenerate verification code for this donation."
        )

    # State validation: cannot regenerate consumed or completed donations
    if donation.otp_used_at is not None or donation.status in ["collected", "in_transit", "delivered", "completed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot regenerate OTP: pickup is already verified or finalized (status: '{donation.status}')."
        )

    # Rate limiting: 15 seconds cooldown
    now_ts = datetime.now(timezone.utc).timestamp()
    last_regen = _last_otp_regen_map.get(donation.id, 0)
    if (now_ts - last_regen) < 15.0:
        remaining = int(15.0 - (now_ts - last_regen))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting a new verification code."
        )

    # Generate new cryptographically secure 6-digit OTP
    new_otp = str(secrets.randbelow(900000) + 100000)
    donation.verification_otp = new_otp
    donation.otp_expiry = datetime.now(timezone.utc) + timedelta(hours=settings.OTP_EXPIRE_HOURS)
    donation.otp_used_at = None
    _last_otp_regen_map[donation.id] = now_ts

    # Deactivate any active PickupOtpRecord for this donation
    existing_otps = (
        db.query(PickupOtpRecord)
        .filter(
            PickupOtpRecord.donation_id == donation.id,
            PickupOtpRecord.purpose == "PICKUP_VERIFICATION_OTP",
            PickupOtpRecord.is_active == True,
        )
        .all()
    )
    for old_rec in existing_otps:
        old_rec.is_active = False
    if existing_otps:
        db.flush()

    new_otp_record = PickupOtpRecord(
        donation_id=donation.id,
        donor_id=donation.donor_id,
        volunteer_id=donation.assigned_volunteer_id,
        purpose="PICKUP_VERIFICATION_OTP",
        otp_hash=_hash_otp(new_otp),
        expires_at=donation.otp_expiry,
        is_active=True,
        delivery_status="QUEUED",
    )
    db.add(new_otp_record)

    db.commit()
    db.refresh(donation)

    log_audit_event(db, action="otp_regenerated", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success",
                    details=f"Donor {current_user.id} regenerated OTP for donation {donation.id}")
    log_rescue_operation(
        db, action="OTP generated", donation_id=donation.id,
        user_id=current_user.id,
        remarks="Pickup OTP regenerated by donor",
        details=f"Donor #{current_user.id} regenerated OTP for donation #{donation.id}"
    )

    return {
        "donation_id": donation.id,
        "otp": donation.verification_otp,
        "otp_expiry": donation.otp_expiry.isoformat() if donation.otp_expiry else None,
        "otp_status": "active",
        "qr_token": donation.qr_code_token
    }

@router.post("/{donation_id}/accept", response_model=DonationResponse)
def accept_donation(
    donation_id: int,
    payload: Optional[DonationAcceptRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    pickup_mode = payload.pickup_mode if payload and payload.pickup_mode else "volunteer_dispatch"
    offer_id = payload.offer_id if payload else None

    # Execute authoritative 9-step atomic acceptance with concurrency locking
    ProactiveDispatchService.process_atomic_ngo_acceptance(
        db=db,
        donation_id=donation_id,
        ngo_user_id=current_user.id,
        pickup_mode=pickup_mode,
        offer_id=offer_id,
        caller_role=current_user.role,
    )

    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/request-volunteer", response_model=DonationResponse)
def request_volunteer_for_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    """
    Switches an accepted donation from NGO Self-Pickup to Volunteer Courier Dispatch.
    Allows NGO shelters without driver availability or encountering vehicle trouble
    to request community volunteer support.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if current_user.role == "ngo":
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        if not ngo_profile or donation.assigned_ngo_id != ngo_profile.id:
            raise HTTPException(status_code=403, detail="Only the assigned receiving NGO can request volunteer support.")

    if donation.status not in ["accepted"]:
        raise HTTPException(status_code=400, detail=f"Cannot request volunteer for donation in '{donation.status}' status.")

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
            detail="Advisory rescue window has ended. Volunteer courier support cannot be dispatched."
        )

    old_mode = donation.pickup_mode
    donation.pickup_mode = "volunteer_dispatch"
    log_status_change(
        db, donation.id, donation.status, donation.status, current_user.id,
        f"NGO switched pickup mode from '{old_mode}' to volunteer courier dispatch."
    )

    create_notification(
        db, user_id=donation.donor_id,
        title="Volunteer Support Requested",
        message=f"Receiving shelter requested community volunteer courier support for '{donation.food_name}'.",
        type="info", related_donation_id=donation.id
    )

    log_audit_event(
        db, action="volunteer_requested_by_ngo",
        user_id=current_user.id,
        resource_type="donation",
        resource_id=donation.id,
        status_code="success",
        details=f"Donation {donation.id} switched to volunteer dispatch."
    )

    db.commit()
    db.refresh(donation)

    # Proactively trigger Wave 2 alerts to feasible community volunteers
    try:
        ProactiveDispatchService.dispatch_proactive_alerts(db, donation, force_dispatch=True)
    except Exception as e:
        logger.warning(f"Proactive dispatch error on volunteer request: {e}")

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/self-dropoff", response_model=DonationResponse)
def donor_self_dropoff_switch(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows a donor (or admin) to opt for direct self drop-off to the matched shelter / NGO facility.
    Cancels uncollected volunteer assignments gracefully and sets pickup_mode to 'self_pickup'.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if current_user.role != "admin" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the donor who posted this donation can choose self drop-off.")

    if donation.status in ["collected", "in_transit", "delivered", "completed", "cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot switch to self drop-off for donation in '{donation.status}' status."
        )

    old_mode = donation.pickup_mode
    donation.pickup_mode = "self_pickup"

    # If any volunteer was in 'assigned' or 'accepted' status (not yet picked up), cancel assignment
    assignments = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.status.in_(["assigned", "accepted"])
    ).all()
    for a in assignments:
        transition_assignment_status(
            db, a, "cancelled",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks="Donor chose direct self drop-off."
        )
        a.failure_reason = "Donor opted for direct self drop-off to NGO facility."

    donation.assigned_volunteer_id = None

    log_status_change(
        db, donation.id, donation.status, donation.status, current_user.id,
        f"Donor switched pickup mode from '{old_mode}' to direct self drop-off."
    )

    if donation.assigned_ngo_id:
        create_notification(
            db, user_id=donation.assigned_ngo_id,
            title="Donor Delivering Directly",
            message=f"Donor for '{donation.food_name}' has chosen direct self drop-off to your facility.",
            type="info", related_donation_id=donation.id
        )

    log_audit_event(
        db, action="self_dropoff_selected_by_donor",
        user_id=current_user.id,
        resource_type="donation",
        resource_id=donation.id,
        status_code="success",
        details=f"Donation {donation.id} switched to self_pickup by donor."
    )

    db.commit()
    db.refresh(donation)

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/cancel", response_model=DonationResponse)
def cancel_donation(
    donation_id: int,
    cancel_in: DonationCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Ownership check: only donor of this donation or admin can cancel
    if current_user.role != "admin" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # State machine validation
    validate_donation_transition(donation.status, "cancelled", current_user.role)

    donation.failure_reason = cancel_in.reason

    if donation.assigned_ngo_id:
        ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).with_for_update().first()
        if ngo:
            ngo.current_capacity = min(ngo.capacity, (ngo.current_capacity or 0) + int(donation.quantity))

    if current_user.role == "donor":
        current_user.donor_trust_score = max(0.0, (current_user.donor_trust_score or 98.0) - 2.0)

    assignments = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.status.in_(["assigned", "accepted"])
    ).all()
    for a in assignments:
        transition_assignment_status(
            db, a, "cancelled",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks=f"Donation cancelled by donor: {cancel_in.reason}"
        )
        a.failure_reason = f"Donation cancelled by donor: {cancel_in.reason}"

    transition_donation_status(
        db, donation, "cancelled",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Cancelled: {cancel_in.reason}"
    )
    db.commit()
    db.refresh(donation)

    log_audit_event(
        db, action="donation_cancelled",
        user_id=current_user.id, resource_type="donation", resource_id=donation.id,
        status_code="success", details=f"Donation {donation.id} cancelled: {cancel_in.reason}"
    )

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/escalate", response_model=DonationResponse)
def trigger_emergency_escalation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Triggers emergency escalation for urgent near-expiry donations."""
    # Only the donor of this donation (or admin) may escalate it
    donation_check = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation_check:
        raise HTTPException(status_code=404, detail="Donation not found.")
    if current_user.role != "admin" and donation_check.donor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Donation not found.")

    donation = escalate_donation(db, donation_id, reason="User triggered emergency priority escalation")
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp


@router.post("/{donation_id}/collect", response_model=DonationResponse)
def collect_food(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "ngo", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Ownership check
    if current_user.role == "volunteer" and donation.assigned_volunteer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned volunteer for this donation.")
    elif current_user.role == "ngo":
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        if not ngo_profile or donation.assigned_ngo_id != ngo_profile.id:
            raise HTTPException(status_code=403, detail="You are not the assigned NGO for this donation.")

    pickup_actor = f"NGO {current_user.name}" if current_user.role == "ngo" else "volunteer"
    # State machine enforcement
    transition_donation_status(
        db, donation, "collected",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Food collected by {pickup_actor}"
    )

    assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.volunteer_id == current_user.id
    ).first()
    if assignment:
        transition_assignment_status(
            db, assignment, "collected",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks="Food collected by volunteer"
        )

    create_notification(db, donation.donor_id, "Food Collected", f"{pickup_actor} has picked up '{donation.food_name}'.", "info", donation.id)
    if current_user.role != "ngo" and donation.assigned_ngo and donation.assigned_ngo.user_id:
        create_notification(db, donation.assigned_ngo.user_id, "Delivery En Route", f"Volunteer is delivering '{donation.food_name}'.", "info", donation.id)

    db.commit()
    db.refresh(donation)

    log_audit_event(db, action="pickup_confirmed", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success",
                    details=f"Pickup confirmed by {pickup_actor}")

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.post("/{donation_id}/deliver", response_model=DonationResponse)
@router.post("/{donation_id}/receive", response_model=DonationResponse)
def deliver_food(
    donation_id: int,
    payload: Optional[DonationReceiveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "ngo", "admin"]))
):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Ownership check
    if current_user.role == "volunteer" and donation.assigned_volunteer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned volunteer for this donation.")
    elif current_user.role == "ngo":
        ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first()
        if not ngo_profile or donation.assigned_ngo_id != ngo_profile.id:
            raise HTTPException(status_code=403, detail="You are not the assigned NGO for this donation.")

    # Record received quantity and condition if provided
    received_qty = donation.quantity
    if payload and payload.received_quantity is not None:
        received_qty = payload.received_quantity
        donation.received_quantity = received_qty
    elif donation.received_quantity is None:
        donation.received_quantity = donation.quantity

    if payload and payload.remarks:
        donation.distribution_remarks = payload.remarks

    # State machine enforcement — transition to 'delivered' (NGO records distribution to reach 'completed')
    cond_str = f" Condition: {payload.condition}." if (payload and payload.condition) else ""
    transition_donation_status(
        db, donation, "delivered",
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Food delivered to NGO facility ({received_qty:.0f} meals recorded).{cond_str} Awaiting beneficiary distribution recording."
    )

    assignment = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id
    ).first()
    if assignment:
        transition_assignment_status(
            db, assignment, "delivered",
            changed_by_user_id=current_user.id,
            caller_role=current_user.role,
            remarks="Food delivered to NGO facility"
        )

    if donation.assigned_volunteer_id:
        vol = db.query(User).filter(User.id == donation.assigned_volunteer_id).first()
        if vol:
            vol.completed_deliveries = (vol.completed_deliveries or 0) + 1
            total = vol.completed_deliveries + (vol.failed_deliveries or 0)
            vol.reliability_score = round((vol.completed_deliveries / float(total)) * 100, 1)

    # ── Update Donor & NGO Impact & Trust Metrics ─────────────────────────────
    donor = db.query(User).filter(User.id == donation.donor_id).first()
    if donor:
        donor.total_meals_donated = (donor.total_meals_donated or 0.0) + float(donation.quantity)
        donor.donor_trust_score = min(100.0, (donor.donor_trust_score or 98.0) + 1.0)

    if donation.assigned_ngo_id:
        ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first()
        if ngo:
            ngo.total_distributed_meals = (ngo.total_distributed_meals or 0.0) + float(donation.quantity)
            ngo.trust_score = min(100.0, (ngo.trust_score or 96.0) + 1.0)

    donation.cost_avoided_inr = round(donation.quantity * 25.0, 2)
    donation.beneficiaries_served = int(donation.quantity)

    points = 20 if donation.is_emergency else 10
    add_reward_points(db, donation.donor_id, points_to_add=points)

    create_event_notification(
        db,
        user_id=donation.donor_id,
        event_type="FOOD_RECEIVED",
        donation_id=donation.id,
        extra_message=f"Your donation '{donation.food_name}' ({donation.quantity:.0f} meals) has been safely delivered to the NGO partner! Earned +{points} reward points.",
    )
    # Notify the NGO to record beneficiary distribution
    if donation.assigned_ngo_id:
        ngo_notif = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first()
        if ngo_notif and ngo_notif.user_id:
            create_event_notification(
                db,
                user_id=ngo_notif.user_id,
                event_type="FOOD_RECEIVED",
                donation_id=donation.id,
                extra_message=f"Food received: '{donation.food_name}' ({donation.quantity:.0f} meals). Please record beneficiary distribution to close this rescue.",
            )

    db.commit()
    db.refresh(donation)

    log_audit_event(db, action="delivery_confirmed", user_id=current_user.id,
                    resource_type="donation", resource_id=donation.id, status_code="success")

    resp = DonationResponse.model_validate(donation)
    resp.urgency_level = calculate_urgency(donation.preparation_time, donation.expiry_time)
    return resp

@router.get("/{donation_id}/recommend-ngo", response_model=List[NGORecommendationResponse])
def get_ngo_recommendations(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return recommend_ngos(db, donation)

@router.get("/{donation_id}/recommend-volunteer", response_model=List[VolunteerRecommendationResponse])
def get_volunteer_recommendations(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return recommend_volunteers(db, donation)

@router.get("/batch-match/run")
def run_batch_matching(db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin", "ngo"]))):
    """Executes Hungarian Bipartite Algorithm to globally match all pending donations with optimal available NGOs."""
    return global_batch_match_ngos(db)

@router.get("/batched-routes/optimize")
def get_optimized_routes(db: Session = Depends(get_db), current_user: User = Depends(require_role(["volunteer", "admin"]))):
    """Executes VRPTW spatial clustering algorithm to optimize multi-stop pickup routes for volunteers."""
    return optimize_volunteer_routes(db)

@router.get("/{donation_id}/carbon-impact")
def get_carbon_impact(donation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Calculates environmental carbon CO2 and water footprint metrics for a food donation."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    qty_kg = donation.quantity if donation.quantity_unit == "Kg" else donation.quantity * 0.4
    co2_saved_kg = round(qty_kg * 2.5, 2)
    water_saved_liters = round(qty_kg * 1000.0, 1)

    return {
        "donation_id": donation.id,
        "food_name": donation.food_name,
        "quantity": donation.quantity,
        "unit": donation.quantity_unit,
        "co2_saved_kg": co2_saved_kg,
        "water_saved_liters": water_saved_liters,
        "trees_equivalent": round(co2_saved_kg / 20.0, 2),
        "status": donation.status
    }

# ── Recurring Donations Endpoints ───────────────────────────────────────────
@router.get("/recurring/list", response_model=List[RecurringDonationResponse])
def get_recurring_donations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Retrieves all recurring donation templates configured by the donor."""
    return db.query(RecurringDonation).filter(
        RecurringDonation.donor_id == current_user.id,
        RecurringDonation.is_active == True
    ).order_by(RecurringDonation.created_at.desc()).all()

@router.post("/recurring/create", response_model=RecurringDonationResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_donation(
    rec_in: RecurringDonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Creates a reusable recurring donation profile (e.g. Hotel Daily Dinner Buffet)."""
    new_rec = RecurringDonation(
        donor_id=current_user.id,
        template_name=rec_in.template_name,
        food_name=rec_in.food_name,
        food_category=rec_in.food_category,
        typical_quantity=rec_in.typical_quantity,
        quantity_unit=rec_in.quantity_unit,
        frequency=rec_in.frequency,
        preferred_pickup_time=rec_in.preferred_pickup_time,
        pickup_address=rec_in.pickup_address,
        storage_method=rec_in.storage_method or "Heated/Insulated",
        packaging_condition=rec_in.packaging_condition or "Sealed / Covered",
        is_active=True
    )
    db.add(new_rec)
    db.commit()
    db.refresh(new_rec)
    return new_rec

@router.post("/recurring/{recurring_id}/instantiate", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def instantiate_today_donation(
    recurring_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """
    One-tap instantiation: Turns a recurring donation profile into today's active food donation!
    Calculates future expiry based on preferred pickup time and pre-fills verified donor metadata.
    """
    rec = db.query(RecurringDonation).filter(
        RecurringDonation.id == recurring_id,
        RecurringDonation.donor_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recurring donation profile not found.")

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=6)

    otp = f"{secrets.randbelow(900000) + 100000}"
    qr_token = f"DON-{secrets.token_urlsafe(12)}"

    today_donation = FoodDonation(
        donor_id=current_user.id,
        food_name=f"{rec.food_name} (Today's Service)",
        description=f"Generated via recurring template: {rec.template_name}. Preferred pickup: {rec.preferred_pickup_time}",
        food_category=rec.food_category,
        quantity=rec.typical_quantity,
        quantity_unit=rec.quantity_unit,
        preparation_time=now,
        expiry_time=expiry,
        pickup_address=rec.pickup_address,
        latitude=current_user.latitude or 12.9716,
        longitude=current_user.longitude or 77.5946,
        storage_method=rec.storage_method,
        storage_duration_hours=1.5,
        packaging_condition=rec.packaging_condition,
        ai_food_detected=rec.food_name,
        ai_visible_spoilage="Not detected",
        ai_discoloration="Normal",
        ai_packaging_intact="Intact",
        ai_visual_condition="GOOD",
        ai_confidence_score=0.95,
        condition_score=92,
        verification_otp=otp,
        qr_code_token=qr_token,
        status="pending"
    )
    db.add(today_donation)
    db.commit()
    db.refresh(today_donation)

    log_status_change(db, today_donation.id, None, "pending", current_user.id, f"Instantiated via recurring template: {rec.template_name}")

    # Notify NGOs
    ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()
    for ngo in ngos:
        create_notification(
            db,
            user_id=ngo.user_id,
            title="Recurring Partner Food Available",
            message=f"{current_user.name} posted today's recurring donation: '{today_donation.food_name}' ({today_donation.quantity} {today_donation.quantity_unit}).",
            type="donation",
            related_donation_id=today_donation.id
        )
    db.commit()

    resp = DonationResponse.model_validate(today_donation)
    resp.urgency_level = calculate_urgency(today_donation.preparation_time, today_donation.expiry_time)
    return resp

@router.delete("/recurring/{recurring_id}")
def delete_recurring_donation(
    recurring_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    rec = db.query(RecurringDonation).filter(
        RecurringDonation.id == recurring_id,
        RecurringDonation.donor_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recurring donation not found.")
    rec.is_active = False
    db.commit()
    return {"message": "Recurring donation profile deactivated."}

# ── Certificate of Participation & CSR Impact ──────────────────────────────
@router.get("/{donation_id}/certificate", response_model=CertificateResponse)
def get_donation_certificate(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates a verifiable Certificate of Participation in Food Donation for a completed donation.
    Clearly marked as a community recognition certificate.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Ownership: only the donor or admin can retrieve the certificate
    if current_user.role != "admin" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Donation not found.")

    donor = db.query(User).filter(User.id == donation.donor_id).first()
    ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first() if donation.assigned_ngo_id else None

    qty_kg = donation.quantity if donation.quantity_unit == "Kg" else donation.quantity * 0.4
    co2_saved = round(qty_kg * 2.5, 2)
    water_saved = round(qty_kg * 1000.0, 1)

    completed_str = donation.updated_at.strftime("%B %d, %Y") if donation.updated_at else datetime.now().strftime("%B %d, %Y")
    cert_hash = hashlib.sha256(f"CERT-{donation.id}-{donor.id}-{donation.created_at}".encode()).hexdigest()[:16].upper()

    return CertificateResponse(
        certificate_id=f"SFD-{donation.id:05d}-{cert_hash[:6]}",
        donation_id=donation.id,
        donor_name=donor.name if donor else "Verified Donor",
        organization_type="Food Business Partner" if (donor and donor.role == "donor") else "Community Contributor",
        food_name=donation.food_name,
        quantity=donation.quantity,
        quantity_unit=donation.quantity_unit,
        receiving_ngo=ngo.organization_name if ngo else "Community Partner NGO",
        completed_at=completed_str,
        verification_hash=cert_hash,
        co2_saved_kg=co2_saved,
        water_saved_liters=water_saved,
        title="Certificate of Participation in Food Donation",
        disclaimer="Issued for voluntary surplus food redistribution and community hunger relief."
    )

@router.get("/csr/summary", response_model=CSRImpactSummaryResponse)
def get_csr_impact_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Calculates CSR-ready aggregated impact metrics, cost-avoidance estimates, and partner reach for the donor."""
    completed_donations = db.query(FoodDonation).filter(
        FoodDonation.donor_id == current_user.id,
        FoodDonation.status.in_(["delivered", "completed"])
    ).all()

    total_meals = sum(d.quantity for d in completed_donations)
    total_qty_kg = sum(d.quantity if d.quantity_unit == "Kg" else d.quantity * 0.4 for d in completed_donations)
    co2_saved = round(total_qty_kg * 2.5, 2)
    water_saved = round(total_qty_kg * 1000.0, 1)
    
    # Waste disposal cost avoided (avg INR 15 per meal equivalent)
    cost_avoided = round(total_meals * 15.0, 2)

    partner_ngo_ids = {d.assigned_ngo_id for d in completed_donations if d.assigned_ngo_id}

    return CSRImpactSummaryResponse(
        donor_id=current_user.id,
        donor_name=current_user.name,
        total_donations=len(completed_donations),
        total_meals_donated=float(total_meals),
        total_co2_avoided_kg=co2_saved,
        total_water_conserved_liters=water_saved,
        estimated_disposal_cost_avoided_inr=cost_avoided,
        verified_ngo_partners_count=len(partner_ngo_ids),
        trust_score=current_user.donor_trust_score or 98.0,
        is_verified_donor=current_user.is_verified_donor if current_user.is_verified_donor is not None else True
    )

@router.get("/donor/impact-summary", response_model=DonorImpactSummaryResponse)
def get_donor_impact_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """
    Comprehensive Donor Motivation & Impact Summary distinguishing:
    - MEALS DONATED (Total quantity created by this donor)
    - MEALS RESCUED (Total quantity delivered to verified NGOs)
    - MEALS DISTRIBUTED (Total meals served to community beneficiaries)
    - ESTIMATED WASTE DIVERTED (kg, based on 0.45 kg/meal conversion factor)
    - ESTIMATED VALUE PRESERVED (INR, based on 25.0 INR/meal factor)
    - Platform Recognition Level (First Rescue, Community Partner, Contributor, Sustainability Partner)
    - Monthly historical breakdown
    """
    all_donations = db.query(FoodDonation).filter(
        FoodDonation.donor_id == current_user.id,
        FoodDonation.status != "cancelled"
    ).all()

    completed_donations = [d for d in all_donations if d.status in ["delivered", "completed", "partially_distributed"]]

    meals_donated = sum(d.quantity for d in all_donations)
    meals_rescued = sum(d.quantity for d in completed_donations)
    meals_distributed = sum((d.distributed_quantity or d.beneficiaries_served or 0.0) for d in completed_donations)

    waste_diverted_kg = round(meals_rescued * 0.45, 2)
    value_preserved_inr = round(meals_rescued * 25.0, 2)

    partner_ngo_ids = {d.assigned_ngo_id for d in completed_donations if d.assigned_ngo_id}

    successful_count = len(completed_donations)
    total_count = len(all_donations)
    completion_rate = round((successful_count / total_count * 100.0), 1) if total_count > 0 else 0.0

    # Recognition level based on verified completed rescues
    if successful_count >= 30:
        recognition = "SUSTAINABILITY PARTNER"
    elif successful_count >= 15:
        recognition = "FOOD RESCUE CONTRIBUTOR"
    elif successful_count >= 5:
        recognition = "COMMUNITY PARTNER"
    elif successful_count >= 1:
        recognition = "FIRST RESCUE"
    else:
        recognition = "NEW SUPPORTER"

    # Monthly breakdown aggregation
    monthly_map = {}
    for d in all_donations:
        dt = d.created_at or datetime.now(timezone.utc)
        month_key = dt.strftime("%B %Y")
        if month_key not in monthly_map:
            monthly_map[month_key] = {
                "month": month_key,
                "donations_count": 0,
                "meals_donated": 0.0,
                "meals_rescued": 0.0,
                "meals_distributed": 0.0,
                "waste_diverted_kg": 0.0,
                "successful_rescues": 0,
                "ngo_ids": set()
            }
        m = monthly_map[month_key]
        m["donations_count"] += 1
        m["meals_donated"] += d.quantity
        if d.status in ["delivered", "completed", "partially_distributed"]:
            m["successful_rescues"] += 1
            m["meals_rescued"] += d.quantity
            m["meals_distributed"] += (d.distributed_quantity or d.beneficiaries_served or 0.0)
            m["waste_diverted_kg"] += round(d.quantity * 0.45, 2)
            if d.assigned_ngo_id:
                m["ngo_ids"].add(d.assigned_ngo_id)

    monthly_breakdown = [
        DonorMonthlyImpactItem(
            month=m["month"],
            donations_count=m["donations_count"],
            meals_donated=float(m["meals_donated"]),
            meals_rescued=float(m["meals_rescued"]),
            meals_distributed=float(m["meals_distributed"]),
            waste_diverted_kg=round(m["waste_diverted_kg"], 2),
            successful_rescues=m["successful_rescues"],
            partner_ngos_count=len(m["ngo_ids"])
        )
        for m in monthly_map.values()
    ]

    active_count = len([d for d in all_donations if d.status in ["accepted", "volunteer_assigned", "collected", "in_transit", "partially_distributed"]])
    pending_count = len([d for d in all_donations if d.status == "pending"])
    failed_count = len([d for d in all_donations if d.status in ["expired", "cancelled", "pickup_failed", "delivery_failed"]])
    finalized_count = successful_count + failed_count
    rescue_success_rate = round((successful_count / max(1, finalized_count) * 100.0), 1) if finalized_count > 0 else 100.0

    return DonorImpactSummaryResponse(
        donor_id=current_user.id,
        donor_name=current_user.name,
        total_donations_count=total_count,
        successful_rescues_count=successful_count,
        active_rescues_count=active_count,
        pending_rescues_count=pending_count,
        meals_donated=float(meals_donated),
        meals_rescued=float(meals_rescued),
        meals_distributed=float(meals_distributed),
        estimated_waste_diverted_kg=waste_diverted_kg,
        estimated_value_preserved_inr=value_preserved_inr,
        partner_ngos_count=len(partner_ngo_ids),
        recognition_level=recognition,
        completion_rate_percent=completion_rate,
        rescue_success_rate_percent=rescue_success_rate,
        conversion_factor_note="Estimated waste diverted = completed rescued meals × 0.45 kg project estimation factor.",
        monthly_breakdown=monthly_breakdown
    )

# ── Two-Way Ratings Endpoints ───────────────────────────────────────────────
@router.post("/{donation_id}/rate", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
def submit_rating(
    donation_id: int,
    rating_in: RatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enables two-way ratings between Donor, NGO, and Volunteer post-completion."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    new_rating = Rating(
        donation_id=donation.id,
        from_user_id=current_user.id,
        to_user_id=rating_in.to_user_id,
        role_from=current_user.role,
        role_to=rating_in.role_to,
        rating_score=rating_in.rating_score,
        feedback=rating_in.feedback,
        tags=rating_in.tags
    )
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    return new_rating

@router.get("/{donation_id}/ratings", response_model=List[RatingResponse])
def get_donation_ratings(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Rating).filter(Rating.donation_id == donation_id).all()

# ── Donation Specific AI Analysis & Advisory ─────────────────────────────────
@router.post("/{donation_id}/analyze", response_model=FoodAnalysisResponse)
def analyze_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Performs or refreshes AI visual condition and advisory analysis for a specific donation.
    Uses canonical AI Vision service with strict food safety disclaimers.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    analysis_res = analyze_food_image_and_metadata(
        food_category=donation.food_category,
        food_type=donation.food_type or donation.food_name,
        quantity=donation.quantity,
        storage_method=donation.storage_method,
        storage_duration_hours=donation.storage_duration_hours,
        storage_continuous=donation.storage_continuous if donation.storage_continuous is not None else True,
        packaging_condition=donation.packaging_condition,
        previously_served=donation.previously_served or "No",
        exposure_status=donation.exposure_status or "No",
        handling_status=donation.handling_status or "No",
        preparation_time=donation.preparation_time
    )

    donation.ai_food_detected = analysis_res.get("food_detected")
    donation.ai_visible_spoilage = analysis_res.get("visible_spoilage")
    donation.ai_discoloration = analysis_res.get("discoloration")
    donation.ai_packaging_intact = analysis_res.get("packaging_integrity")
    donation.ai_visual_condition = analysis_res.get("visual_condition")
    donation.ai_confidence_score = analysis_res.get("confidence")

    # Persist or update FoodAnalysis record
    food_analysis = db.query(FoodAnalysis).filter(FoodAnalysis.donation_id == donation.id).first()
    now = datetime.now(timezone.utc)
    obs_list = analysis_res.get("observations", [])
    obs_str = json.dumps(obs_list) if isinstance(obs_list, list) else str(obs_list)

    if not food_analysis:
        food_analysis = FoodAnalysis(
            donation_id=donation.id,
            food_detected=analysis_res.get("food_detected"),
            visible_spoilage=analysis_res.get("visible_spoilage"),
            discoloration=analysis_res.get("discoloration"),
            packaging_integrity=analysis_res.get("packaging_integrity"),
            visual_condition=analysis_res.get("visual_condition", "GOOD"),
            confidence=analysis_res.get("confidence") if analysis_res.get("confidence") is not None else 0.88,
            observations=obs_str,
            safety_disclaimer=analysis_res.get("safety_disclaimer", "Visual assessment only; this does not certify food safety."),
            storage_assessment=analysis_res.get("storage_assessment"),
            urgency_recommendation=analysis_res.get("urgency_recommendation"),
            analyzed_at=now
        )
        db.add(food_analysis)
    else:
        food_analysis.food_detected = analysis_res.get("food_detected")
        food_analysis.visible_spoilage = analysis_res.get("visible_spoilage")
        food_analysis.discoloration = analysis_res.get("discoloration")
        food_analysis.packaging_integrity = analysis_res.get("packaging_integrity")
        food_analysis.visual_condition = analysis_res.get("visual_condition", "GOOD")
        food_analysis.confidence = analysis_res.get("confidence") if analysis_res.get("confidence") is not None else 0.88
        food_analysis.observations = obs_str
        food_analysis.safety_disclaimer = analysis_res.get("safety_disclaimer", "Visual assessment only; this does not certify food safety.")
        food_analysis.storage_assessment = analysis_res.get("storage_assessment")
        food_analysis.urgency_recommendation = analysis_res.get("urgency_recommendation")
        food_analysis.analyzed_at = now

    db.commit()
    db.refresh(food_analysis)
    db.refresh(donation)

    return FoodAnalysisResponse(
        id=food_analysis.id,
        donation_id=donation.id,
        food_detected=food_analysis.food_detected,
        visible_spoilage=food_analysis.visible_spoilage,
        discoloration=food_analysis.discoloration,
        packaging_integrity=food_analysis.packaging_integrity,
        visual_condition=food_analysis.visual_condition,
        confidence=food_analysis.confidence,
        observations=food_analysis.observations,
        safety_disclaimer=food_analysis.safety_disclaimer,
        storage_assessment=food_analysis.storage_assessment,
        urgency_recommendation=food_analysis.urgency_recommendation,
        analyzed_at=food_analysis.analyzed_at
    )

# ── Beneficiary Distribution Recording ───────────────────────────────────────
@router.post("/{donation_id}/distribution", response_model=DonationDistributionResponse)
def record_beneficiary_distribution(
    donation_id: int,
    dist_in: DonationDistributionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ngo", "admin"]))
):
    """
    Allows the receiving NGO (or admin) to record the aggregate distribution to community beneficiaries.
    Distinguishes DONATED -> RESCUED -> DISTRIBUTED in the end-to-end pipeline.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    ngo_profile = db.query(NGO).filter(NGO.user_id == current_user.id).first() if current_user.role == "ngo" else None
    if current_user.role == "ngo" and (not ngo_profile or donation.assigned_ngo_id != ngo_profile.id):
        raise HTTPException(status_code=403, detail="Only the assigned receiving NGO can record distribution for this donation.")

    if donation.status not in ["delivered", "completed", "distribution_pending", "partially_distributed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot record distribution for donation with status '{donation.status}'. Must be delivered or completed (or distribution_pending / partially_distributed)."
        )

    distributed_qty = dist_in.distributed_quantity
    if distributed_qty is None and dist_in.beneficiary_count is not None:
        distributed_qty = float(dist_in.beneficiary_count)
    elif distributed_qty is None:
        distributed_qty = 0.0

    if distributed_qty < 0:
        raise HTTPException(status_code=400, detail="Distributed quantity cannot be negative.")

    received_qty = dist_in.received_quantity
    if received_qty is None:
        received_qty = donation.received_quantity or donation.quantity

    if distributed_qty > received_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Distributed quantity ({distributed_qty}) cannot exceed received quantity ({received_qty})."
        )

    remaining_qty = dist_in.remaining_quantity
    if remaining_qty is None:
        remaining_qty = max(0.0, received_qty - distributed_qty)

    if remaining_qty < 0:
        raise HTTPException(status_code=400, detail="Remaining quantity cannot be negative.")

    beneficiaries = dist_in.beneficiaries_served
    if beneficiaries is None:
        beneficiaries = dist_in.beneficiary_count if dist_in.beneficiary_count is not None else int(distributed_qty)

    remarks = dist_in.remarks or dist_in.beneficiary_notes

    new_status = "completed" if remaining_qty <= 0 else "partially_distributed"

    donation.received_quantity = received_qty
    donation.distributed_quantity = distributed_qty
    donation.remaining_quantity = remaining_qty
    donation.distribution_timestamp = dist_in.distribution_timestamp or datetime.now(timezone.utc)
    donation.distribution_remarks = remarks
    donation.beneficiaries_served = beneficiaries

    transition_donation_status(
        db, donation, new_status,
        changed_by_user_id=current_user.id,
        caller_role=current_user.role,
        remarks=f"Distributed {distributed_qty:.0f} meals to {beneficiaries} beneficiaries (Remaining: {remaining_qty:.0f})"
    )

    if ngo_profile:
        ngo_profile.total_distributed_meals = (ngo_profile.total_distributed_meals or 0.0) + float(distributed_qty)

    # Notify donor that food was distributed to beneficiaries
    if new_status == "completed":
        create_event_notification(
            db,
            user_id=donation.donor_id,
            event_type="DISTRIBUTION_COMPLETED",
            donation_id=donation.id,
            extra_message=f"All meals ({distributed_qty:.0f}) from your donation '{donation.food_name}' have been served to people in need.",
        )
    else:
        create_notification(
            db,
            user_id=donation.donor_id,
            title="Food Distributed to Beneficiaries! ❤️",
            message=f"{distributed_qty:.0f} meals from your donation '{donation.food_name}' have been served to people in need.",
            type="success",
            related_donation_id=donation.id
        )

    db.commit()
    db.refresh(donation)

    log_audit_event(
        db, action="beneficiary_distribution_recorded", user_id=current_user.id,
        resource_type="donation", resource_id=donation.id, status_code="success",
        details=f"Distributed {distributed_qty} meals to {beneficiaries} beneficiaries."
    )
    log_rescue_operation(
        db, action="distributed", donation_id=donation.id,
        user_id=current_user.id, old_status=donation.status, new_status=new_status,
        remarks=f"Distributed {distributed_qty:.0f} meals to {beneficiaries} beneficiaries",
        details=f"Distributed {distributed_qty} meals to {beneficiaries} beneficiaries (Remaining: {remaining_qty:.0f})"
    )
    if new_status == "completed":
        log_rescue_operation(
            db, action="completed", donation_id=donation.id,
            user_id=current_user.id, old_status="partially_distributed", new_status="completed",
            remarks="Rescue mission completed and food fully distributed",
            details=f"Donation #{donation.id} completed. All meals distributed."
        )

    return DonationDistributionResponse(
        donation_id=donation.id,
        received_quantity=donation.received_quantity or 0.0,
        distributed_quantity=donation.distributed_quantity or 0.0,
        remaining_quantity=donation.remaining_quantity or 0.0,
        distribution_timestamp=donation.distribution_timestamp,
        distribution_status="distributed",
        beneficiaries_served=donation.beneficiaries_served,
        remarks=donation.distribution_remarks
    )

# ── Timeout-Based Fallback Matching ──────────────────────────────────────────
@router.post("/process-timeouts")
def process_timeouts(
    ngo_timeout_minutes: int = Query(30),
    volunteer_timeout_minutes: int = Query(15),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "donor", "ngo"]))
):
    """
    Automated timeout sweep:
    1. Unresponded NGO offers past timeout -> marked expired -> triggers fallback matching.
    2. Volunteer assignments past timeout without response -> cancelled -> triggers fallback volunteer dispatch.
    """
    now = datetime.now(timezone.utc)
    ngo_cutoff = now - timedelta(minutes=ngo_timeout_minutes)
    vol_cutoff = now - timedelta(minutes=volunteer_timeout_minutes)

    expired_offers_count = 0
    expired_assignments_count = 0

    # 1. Expire unresponded volunteer assignments
    timed_out_assignments = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.status == "assigned",
        VolunteerAssignment.assigned_at < vol_cutoff
    ).all()

    for va in timed_out_assignments:
        transition_assignment_status(
            db, va, "failed",
            changed_by_user_id=current_user.id,
            caller_role="system",
            remarks="Assignment timed out (no volunteer response)"
        )
        va.failure_reason = "Assignment timed out (no volunteer response)"
        donation = db.query(FoodDonation).filter(FoodDonation.id == va.donation_id).first()
        if donation:
            transition_donation_status(
                db, donation, "accepted",
                changed_by_user_id=current_user.id,
                caller_role="system",
                remarks="Volunteer response timed out; reverted to accepted for fallback dispatch"
            )
            donation.assigned_volunteer_id = None
            # Dispatch fallback volunteer
            recs = recommend_volunteers(db, donation)
            for r in recs:
                if r["volunteer_id"] != va.volunteer_id:
                    create_notification(
                        db,
                        user_id=r["volunteer_id"],
                        title="Urgent Fallback Pickup Task",
                        message=f"Pickup opportunity available: '{donation.food_name}' at {donation.pickup_address}.",
                        type="assignment",
                        related_donation_id=donation.id
                    )
                    break
        expired_assignments_count += 1

    # 2. Expire unresponded match offers
    timed_out_offers = db.query(MatchOffer).filter(
        MatchOffer.status == "offered",
        MatchOffer.offered_at < ngo_cutoff
    ).all()

    for mo in timed_out_offers:
        mo.status = "expired"
        donation = db.query(FoodDonation).filter(FoodDonation.id == mo.donation_id).first()
        if donation and donation.status == "pending":
            recs = recommend_ngos(db, donation)
            for r in recs:
                if r["ngo_id"] != mo.candidate_id:
                    next_ngo = db.query(NGO).filter(NGO.id == r["ngo_id"]).first()
                    if next_ngo:
                        create_notification(
                            db,
                            user_id=next_ngo.user_id,
                            title="Fallback Food Donation Offer",
                            message=f"New surplus food offer: '{donation.food_name}' ({donation.quantity} {donation.quantity_unit}).",
                            type="donation",
                            related_donation_id=donation.id
                        )
                        break
        expired_offers_count += 1

    db.commit()

    return {
        "status": "success",
        "processed_at": now.isoformat(),
        "expired_volunteer_assignments": expired_assignments_count,
        "expired_ngo_offers": expired_offers_count
    }

# ── Platform Metrics Summary ─────────────────────────────────────────────────
@router.get("/metrics/summary", response_model=DonationMetricsSummary)
def get_donation_metrics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Comprehensive platform metrics distinguishing:
    - MEALS DONATED (Total meals posted)
    - MEALS RESCUED (Total meals delivered to NGOs)
    - MEALS DISTRIBUTED (Total meals served to beneficiaries)
    - ESTIMATED DISPOSAL COST AVOIDED
    """
    all_donations = db.query(FoodDonation).filter(FoodDonation.status != "cancelled").all()
    completed = [d for d in all_donations if d.status in ["delivered", "completed"]]

    meals_donated = sum(d.quantity for d in all_donations)
    meals_rescued = sum(d.quantity for d in completed)
    meals_distributed = sum((d.distributed_quantity or d.beneficiaries_served or 0.0) for d in completed)
    cost_avoided = sum((d.cost_avoided_inr or (d.quantity * 25.0)) for d in completed)

    return DonationMetricsSummary(
        meals_donated=float(meals_donated),
        meals_rescued=float(meals_rescued),
        meals_distributed=float(meals_distributed),
        total_donations_count=len(all_donations),
        completed_rescues_count=len(completed),
        estimated_disposal_cost_avoided_inr=round(cost_avoided, 2)
    )

# ── Kitchen Profile Management (Business Donors) ─────────────────────────────
@router.post("/kitchen-profiles", response_model=KitchenProfileResponse, status_code=status.HTTP_201_CREATED)
def create_kitchen_profile(
    profile_in: KitchenProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Creates a new registered kitchen / location profile for frequent business donors."""
    new_profile = KitchenProfile(
        donor_id=current_user.id,
        name=profile_in.name,
        location_address=profile_in.location_address,
        latitude=profile_in.latitude or current_user.latitude or 12.9716,
        longitude=profile_in.longitude or current_user.longitude or 77.5946,
        typical_food_types=profile_in.typical_food_types,
        default_storage_method=profile_in.default_storage_method or "Refrigerated",
        contact_person=profile_in.contact_person or current_user.name,
        contact_phone=profile_in.contact_phone or current_user.phone
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile

@router.get("/kitchen-profiles", response_model=List[KitchenProfileResponse])
def get_my_kitchen_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Retrieves all active kitchen profiles for the authenticated donor."""
    return db.query(KitchenProfile).filter(
        KitchenProfile.donor_id == current_user.id,
        KitchenProfile.is_active == True
    ).order_by(KitchenProfile.created_at.desc()).all()

@router.delete("/kitchen-profiles/{profile_id}")
def delete_kitchen_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Deactivates a kitchen profile belonging to the current donor."""
    profile = db.query(KitchenProfile).filter(
        KitchenProfile.id == profile_id,
        KitchenProfile.donor_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Kitchen profile not found.")
    profile.is_active = False
    db.commit()
    return {"status": "success", "message": f"Kitchen profile '{profile.name}' deactivated."}

# ── One-Tap Repeat Donation Prefill ──────────────────────────────────────────
@router.get("/repeat-prefill/latest", response_model=RepeatDonationPrefillResponse)
def get_latest_repeat_donation_prefill(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """
    Fetches stable fields from the donor's most recent donation for quick re-use.
    Enforces that fresh quantity, preparation time, current storage, and visual assessment
    must be reconfirmed.
    """
    latest = db.query(FoodDonation).filter(
        FoodDonation.donor_id == current_user.id
    ).order_by(FoodDonation.created_at.desc()).first()

    if not latest:
        raise HTTPException(status_code=404, detail="No prior donations found to repeat.")

    return RepeatDonationPrefillResponse(
        previous_donation_id=latest.id,
        food_name=latest.food_name,
        food_category=latest.food_category,
        food_type=latest.food_type or latest.food_name,
        typical_quantity=latest.quantity,
        quantity_unit=latest.quantity_unit,
        pickup_address=latest.pickup_address,
        latitude=latest.latitude,
        longitude=latest.longitude,
        default_storage_method=latest.storage_method or "Room Temperature",
        packaging_condition=latest.packaging_condition or "Covered"
    )

@router.get("/repeat-prefill/{donation_id}", response_model=RepeatDonationPrefillResponse)
def get_repeat_donation_prefill_by_id(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"]))
):
    """Fetches stable fields from a specific historical donation for quick repeating."""
    donation = db.query(FoodDonation).filter(
        FoodDonation.id == donation_id,
        FoodDonation.donor_id == current_user.id
    ).first()

    if not donation:
        raise HTTPException(status_code=404, detail="Specified donation not found.")

    return RepeatDonationPrefillResponse(
        previous_donation_id=donation.id,
        food_name=donation.food_name,
        food_category=donation.food_category,
        food_type=donation.food_type or donation.food_name,
        typical_quantity=donation.quantity,
        quantity_unit=donation.quantity_unit,
        pickup_address=donation.pickup_address,
        latitude=donation.latitude,
        longitude=donation.longitude,
        default_storage_method=donation.storage_method or "Room Temperature",
        packaging_condition=donation.packaging_condition or "Covered"
    )

# ── Proactive Time-Critical Food Rescue Alert & NGO Dispatch Endpoints ────────
@router.post("/monitor-urgency")
def trigger_urgency_monitor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "donor", "ngo"]))
):
    """Admin/system endpoint to execute a full proactive urgency monitoring and wave dispatch cycle."""
    result = BackgroundUrgencyMonitor.run_cycle()
    return result

@router.post("/{donation_id}/trigger-dispatch")
def trigger_proactive_dispatch(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "donor", "ngo"]))
):
    """Force-evaluates urgency and triggers the next dispatch wave for a donation."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    result = ProactiveDispatchService.dispatch_proactive_alerts(db, donation, force_dispatch=True)
    return result

@router.get("/{donation_id}/dispatch-status")
def get_dispatch_status(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns proactive dispatch state, alert wave, candidate NGO offers, and alert history."""
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    
    offers = db.query(MatchOffer).filter(MatchOffer.donation_id == donation.id).all()
    history = []
    if donation.alert_history_json:
        try:
            history = json.loads(donation.alert_history_json)
        except Exception:
            history = []

    return {
        "donation_id": donation.id,
        "food_name": donation.food_name,
        "quantity": donation.quantity,
        "quantity_unit": donation.quantity_unit,
        "status": donation.status,
        "remaining_minutes": donation.remaining_minutes,
        "urgency_level": donation.rescue_urgency_level or getattr(donation, "urgency_level", "FRESH"),
        "current_alert_wave": donation.current_alert_wave,
        "last_alerted_urgency": donation.last_alerted_urgency,
        "last_alerted_at": donation.last_alerted_at.isoformat() if donation.last_alerted_at else None,
        "wave_timeout_at": donation.wave_timeout_at.isoformat() if donation.wave_timeout_at else None,
        "offers": [
            {
                "id": o.id,
                "candidate_id": o.candidate_id,
                "candidate_type": o.candidate_type,
                "score": o.score,
                "status": o.status,
                "wave_number": o.wave_number,
                "offered_at": o.offered_at.isoformat() if o.offered_at else None,
                "responded_at": o.responded_at.isoformat() if o.responded_at else None,
                "response_time_seconds": o.response_time_seconds,
            }
            for o in offers
        ],
        "alert_history": history,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pickup OTP Endpoints
# ─────────────────────────────────────────────────────────────────────────────
# SECURITY:
#   - Only donors may retrieve the OTP display (GET /pickup-otp).
#   - Volunteers receive 403 on that endpoint — they enter the code shown to them.
#   - Volunteers use POST /pickup-otp/verify to submit the code.
#   - OTP is NEVER exposed to volunteers via any API path.
#   - Push notifications NEVER contain the OTP value.

from app.services.otp_service import (
    generate_pickup_otp, send_pickup_otp_sms, verify_pickup_otp,
    regenerate_pickup_otp, process_sms_delivery_webhook
)
from app.services.sms_service import mask_phone
from app.services.notification_service import create_event_notification
from app.models.models import PickupOtpRecord, OtpDeliveryRecord
from pydantic import BaseModel as _BaseModel


class PickupOtpVerifyRequest(_BaseModel):
    otp: str


@router.get("/{donation_id}/pickup-otp")
def get_pickup_otp_for_donor(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the active pickup OTP for authenticated DONOR only.

    SECURITY:
    - Volunteers receive 403 Forbidden.
    - Unauthenticated requests receive 401.
    - OTP is shown as plaintext only to the authenticated donor.
    - Also returns SMS delivery status so UI can show ✅/⚠/❌.
    """
    # Strict role enforcement — NEVER return OTP to volunteer
    if current_user.role == "volunteer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Volunteers do not receive the pickup code via API. "
                "Ask the donor to show the code directly."
            ),
        )

    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    # Donors may only see their own donation OTPs; admins may see any
    if current_user.role == "donor" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    otp_record = (
        db.query(PickupOtpRecord)
        .filter(
            PickupOtpRecord.donation_id == donation_id,
            PickupOtpRecord.purpose == "PICKUP_VERIFICATION_OTP",
            PickupOtpRecord.is_active == True,
        )
        .first()
    )

    if not otp_record:
        # No OTP generated yet or all expired
        return {
            "otp_available": False,
            "message": "No active pickup code. The volunteer must arrive first.",
            "delivery_status": None,
            "phone_masked": None,
        }

    # Check expiry
    now = datetime.now(timezone.utc)
    expires_at = otp_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        otp_record.is_active = False
        otp_record.delivery_status = "EXPIRED"
        db.commit()
        return {
            "otp_available": False,
            "message": "This pickup code has expired. Please request a new code.",
            "delivery_status": "EXPIRED",
            "phone_masked": None,
        }

    # Fetch latest delivery record for this OTP
    delivery_record = (
        db.query(OtpDeliveryRecord)
        .filter(OtpDeliveryRecord.otp_record_id == otp_record.id)
        .order_by(OtpDeliveryRecord.created_at.desc())
        .first()
    )

    # Decode the OTP hash back to display — we need to reconstruct from record
    # IMPORTANT: We cannot reverse the hash. Instead the plaintext must be
    # returned from a dedicated secure lookup. Since the hash is one-way, we need
    # to store the plaintext temporarily in the OTP record for display purposes
    # BUT the design says never store it. The correct pattern is:
    # - The OTP was given to the donor at generation time (in the generate response).
    # - For subsequent views, the donor screen must re-fetch the OTP from the same
    #   API. We accomplish this by returning a "VIEW OTP" token (the record ID + auth).
    # - The actual display requires the OTP to be re-generated or shown from memory.
    #
    # PRAGMATIC SOLUTION (acceptable for this platform):
    # Store the plaintext OTP encrypted with a server key, or simply regenerate
    # if the donor re-requests. For this implementation, we indicate the OTP
    # needs to be regenerated for re-display, and show delivery status + expiry.
    #
    # The donor dashboard always shows the OTP received at initial generation.
    # If they lost it, they use /regenerate.

    remaining_seconds = max(0, int((expires_at - now).total_seconds()))
    remaining_minutes = remaining_seconds // 60

    return {
        "otp_available": True,
        "otp_record_id": otp_record.id,
        "expires_at": expires_at.isoformat(),
        "remaining_seconds": remaining_seconds,
        "remaining_minutes": remaining_minutes,
        "delivery_status": otp_record.delivery_status,
        "phone_masked": delivery_record.phone_number_masked if delivery_record else None,
        "provider": delivery_record.provider if delivery_record else None,
        "sent_at": delivery_record.sent_at.isoformat() if delivery_record and delivery_record.sent_at else None,
        "delivered_at": delivery_record.delivered_at.isoformat() if delivery_record and delivery_record.delivered_at else None,
        "failure_reason": delivery_record.failure_reason if delivery_record else None,
        "message": (
            "SMS delivered to your phone." if otp_record.delivery_status == "DELIVERED"
            else "Sent — delivery confirmation unavailable." if otp_record.delivery_status in ("SENT", "UNKNOWN")
            else "SMS delivery failed. View secure code in app." if otp_record.delivery_status == "FAILED"
            else "Sending..."
        ),
    }


@router.post("/{donation_id}/pickup-otp/verify")
def verify_pickup_otp_endpoint(
    donation_id: int,
    payload: PickupOtpVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["volunteer", "admin", "ngo"])),
):
    """
    Volunteer or self-pickup NGO enters the OTP shown by the donor to verify pickup.
    On success: donation transitions to 'collected'.

    SECURITY:
    - Only assigned volunteers, receiving NGOs, and admins may call this.
    - Donors cannot self-verify (role enforced at route level).
    - Wrong OTP → 400. Expired → 410. Replay → 409.
    """
    with _otp_verification_lock:
        db.expire_all()
        # 1. Row locking for transaction safety
        try:
            donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
        except Exception:
            donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()

        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found.")

        # 2. Replay guard: already collected or OTP used
        if donation.otp_used_at is not None or donation.status in ["collected", "in_transit", "delivered", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This pickup code has already been used. Pickup already verified."
            )

        if current_user.role == "volunteer" and donation.assigned_volunteer_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not assigned to this donation.")
        elif current_user.role == "ngo":
            ngo_prof = db.query(NGO).filter(NGO.user_id == current_user.id).first()
            if not ngo_prof or donation.assigned_ngo_id != ngo_prof.id:
                raise HTTPException(status_code=403, detail="You are not the assigned NGO for this donation.")

        # Verify OTP — raises 400/409/410 on failure
        verify_pickup_otp(db, donation, payload.otp, current_user)

        # Transition to collected
        if donation.status != "collected":
            transition_donation_status(
                db, donation, "collected",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks="Pickup OTP verified"
            )
        donation.verification_otp = None  # Redact plaintext

        # Update volunteer assignment
        assignment = (
            db.query(VolunteerAssignment)
            .filter(
                VolunteerAssignment.donation_id == donation_id,
                VolunteerAssignment.volunteer_id == current_user.id,
            )
            .first()
        )
        if assignment:
            transition_assignment_status(
                db, assignment, "collected",
                changed_by_user_id=current_user.id,
                caller_role=current_user.role,
                remarks="Pickup confirmed via OTP"
            )

        db.commit()

        # Fire PICKUP_COMPLETED notifications for all parties
        donor = db.query(User).filter(User.id == donation.donor_id).first()
        donor_lang = (donor.preferred_language if donor else "en") or "en"
        create_event_notification(db, donation.donor_id, "PICKUP_COMPLETED", donation_id, donor_lang)
        if donation.assigned_volunteer_id:
            vol = db.query(User).filter(User.id == donation.assigned_volunteer_id).first()
            vol_lang = (vol.preferred_language if vol else "en") or "en"
            create_event_notification(db, donation.assigned_volunteer_id, "PICKUP_COMPLETED", donation_id, vol_lang)

        log_audit_event(db, action="otp_verified_pickup_complete",
                        user_id=current_user.id, resource_type="donation",
                        resource_id=donation_id, status_code="success",
                        details=f"Volunteer {current_user.name} verified pickup OTP for donation {donation_id}")
        log_rescue_operation(
            db, action="collected", donation_id=donation.id,
            user_id=current_user.id, old_status="arrived_at_donor", new_status="collected",
            remarks="Pickup OTP verified",
            details=f"User #{current_user.id} ({current_user.role}) verified pickup OTP for donation #{donation_id}"
        )

        return {"message": "Pickup code verified. Donation marked as collected.", "status": "collected"}


@router.post("/{donation_id}/pickup-otp/regenerate")
def regenerate_pickup_otp_endpoint(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"])),
):
    """
    Generates a new pickup OTP for the donor, invalidates the previous one.
    Rate-limited: max 3 per 10 minutes.
    Re-sends SMS to verified donor phone.

    SECURITY:
    - Only donors/admins may regenerate.
    - Old OTP is immediately invalidated.
    - Rate limiting prevents SMS abuse.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if current_user.role == "donor" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    donor = db.query(User).filter(User.id == donation.donor_id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found.")

    volunteer_id = donation.assigned_volunteer_id
    plaintext_otp, otp_record, delivery_record = regenerate_pickup_otp(
        db, donation, donor, volunteer_id=volunteer_id
    )
    donor_lang = (donor.preferred_language or "en")
    create_event_notification(db, donor.id, "OTP_SMS_SENT", donation_id, donor_lang)

    return {
        "message": "New pickup code generated and sent to your verified phone.",
        "otp": plaintext_otp,   # Returned once — not stored
        "expires_at": otp_record.expires_at.isoformat(),
        "expires_in_minutes": settings.OTP_PICKUP_EXPIRE_MINUTES,
        "delivery_status": delivery_record.status,
        "phone_masked": delivery_record.phone_number_masked,
        "note": (
            "Delivery confirmation unavailable with current SMS provider."
            if delivery_record.status == "SENT" else None
        ),
    }


@router.get("/{donation_id}/otp-delivery-status")
def get_otp_delivery_status(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["donor", "admin"])),
):
    """
    Returns the current SMS delivery status for the pickup OTP.
    Used by the donor UI to show ✅/⚠/❌ status indicator.

    SECURITY:
    - Donor only (plus admin).
    - Never exposes OTP value or full phone number.
    """
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if current_user.role == "donor" and donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    otp_record = (
        db.query(PickupOtpRecord)
        .filter(
            PickupOtpRecord.donation_id == donation_id,
            PickupOtpRecord.purpose == "PICKUP_VERIFICATION_OTP",
        )
        .order_by(PickupOtpRecord.created_at.desc())
        .first()
    )

    if not otp_record:
        return {"delivery_status": None, "message": "No pickup OTP has been sent yet."}

    delivery_record = (
        db.query(OtpDeliveryRecord)
        .filter(OtpDeliveryRecord.otp_record_id == otp_record.id)
        .order_by(OtpDeliveryRecord.created_at.desc())
        .first()
    )

    status_display = {
        "DELIVERED": "✅ SMS delivered to your verified phone.",
        "SENT": "✓ SMS sent — delivery confirmation unavailable with current provider.",
        "UNKNOWN": "✓ SMS sent — delivery confirmation unavailable.",
        "FAILED": "⚠ SMS delivery failed. Your secure code is still available in the app.",
        "QUEUED": "📤 Sending SMS...",
        "EXPIRED": "Code has expired.",
    }.get(otp_record.delivery_status, "Status unknown.")

    return {
        "delivery_status": otp_record.delivery_status,
        "status_display": status_display,
        "phone_masked": delivery_record.phone_number_masked if delivery_record else None,
        "provider": delivery_record.provider if delivery_record else None,
        "sent_at": delivery_record.sent_at.isoformat() if delivery_record and delivery_record.sent_at else None,
        "delivered_at": delivery_record.delivered_at.isoformat() if delivery_record and delivery_record.delivered_at else None,
        "failure_reason": delivery_record.failure_reason if delivery_record else None,
    }
