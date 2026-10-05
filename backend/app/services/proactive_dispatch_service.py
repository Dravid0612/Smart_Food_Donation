import json
import logging
import math
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.db.session import SessionLocal
from app.models.models import (
    FoodDonation,
    NGO,
    User,
    Notification,
    MatchOffer,
    DonationHistory,
    RescueIssueReport,
    AuditLog,
    VolunteerAssignment,
)
from app.services.food_rescue_window_service import (
    evaluate_food_rescue_window,
    calculate_rescue_feasibility,
)
from app.services.notification_service import create_notification, create_event_notification
from app.services.recommendation_service import (
    haversine_distance,
    is_ngo_open_now,
    calculate_demand_match_score,
)
from app.services.state_machine_service import (
    transition_donation_state,
    transition_donation_status,
    DonationStatus,
)
from app.services.security_service import log_audit_event, log_rescue_operation

logger = logging.getLogger("smart_food_rescue.proactive_dispatch")

# ── Configurable Urgency Thresholds (in remaining minutes) ────────────────────
THRESHOLD_FRESH_MINUTES = 180       # > 3 hours
THRESHOLD_APPROACHING_MINUTES = 120 # 2 - 3 hours
THRESHOLD_URGENT_MINUTES = 45       # 45m - 2 hours
THRESHOLD_CRITICAL_MINUTES = 0      # 1m - 45m (0 or below is RESCUE_WINDOW_ENDED)

# Wave timeouts (in minutes)
WAVE_TIMEOUT_URGENT_MINUTES = 10
WAVE_TIMEOUT_CRITICAL_MINUTES = 5
ALERT_COOLDOWN_MINUTES = 15

# Wave batch sizes
WAVE_1_SIZE = 3
WAVE_2_SIZE = 5

URGENCY_ORDER = {
    "FRESH": 0,
    "APPROACHING": 1,
    "URGENT": 2,
    "CRITICAL": 3,
    "RESCUE_WINDOW_ENDED": 4,
}


def _utcnow() -> datetime:
    """Authoritative server-side current UTC datetime."""
    return datetime.now(timezone.utc)


def _extract_approximate_area(address: Optional[str]) -> str:
    """
    Extracts privacy-safe approximate neighborhood from full address string.
    Never exposes exact door/flat numbers or private street lines in broadcast alerts.
    """
    if not address:
        return "Local area"
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 3:
        # e.g. "123, 4th Cross, Koramangala 5th Block, Bangalore" -> "Koramangala 5th Block area"
        return f"{parts[-2]} area"
    elif len(parts) == 2:
        return f"{parts[0]} area"
    return f"{address} area"


# ── Trilingual Localized Alert Templates ─────────────────────────────────────
def format_proactive_alert_message(
    role: str,
    urgency: str,
    language: str = "en",
    food_name: str = "Food",
    quantity: float = 0.0,
    quantity_unit: str = "Meals",
    distance_km: Optional[float] = None,
    area_name: str = "nearby area",
    remaining_minutes: int = 0,
    food_category: Optional[str] = None,
    pickup_address: Optional[str] = None,
    safety_advisory: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generates natural, non-machine-like trilingual alerts for Donor, NGO, Volunteer, and Admin.
    """
    lang = (language or "en").lower()
    formatted_qty = int(quantity) if (hasattr(quantity, "is_integer") and quantity.is_integer()) or int(quantity) == quantity else f"{quantity:.1f}"
    qty_str = f"{formatted_qty} {quantity_unit}"
    dist_str = f"~{distance_km:.1f} km away in {area_name}" if distance_km is not None else area_name

    if role == "donor":
        if urgency == "APPROACHING":
            if lang == "ta":
                return (
                    "உணவு மீட்பு காலக்கெடு நெருங்குகிறது",
                    f"உங்கள் '{food_name}' நன்கொடைக்கான மீட்பு நேரம் குறைகிறது. தகுதியான NGO-க்கள் கண்காணிக்கப்படுகின்றன."
                )
            elif lang == "hi":
                return (
                    "भोजन बचाव समय निकट आ रहा है",
                    f"आपके '{food_name}' दान का बचाव समय कम हो रहा है। हम उपयुक्त एनजीओ की निगरानी कर रहे हैं।"
                )
            return (
                "Food Donation Becoming Time-Sensitive",
                f"The estimated rescue window for '{food_name}' is progressing. Nearby verified partners are being monitored."
            )
        elif urgency == "URGENT":
            if lang == "ta":
                return (
                    "உங்கள் உணவு நன்கொடை அவசர மீட்பு நிலையை அடைந்துள்ளது",
                    f"மதிப்பிடப்பட்ட மீட்பு நேரம் குறைவாக உள்ளது (~{remaining_minutes} நிமிடம்). அருகிலுள்ள தகுதியான NGO-க்களுக்கு முன்னுரிமை அளிக்கப்படுகிறது."
                )
            elif lang == "hi":
                return (
                    "आपका भोजन दान समय-संवेदनशील हो गया है",
                    f"अनुमानित बचाव समय सीमित है (~{remaining_minutes} मिनट शेष)। हम निकटतम व्यवहार्य बचाव भागीदारों को प्राथमिकता दे रहे हैं।"
                )
            return (
                "Your Food Donation is Becoming Time-Critical",
                f"The estimated rescue window is limited (~{remaining_minutes}m remaining). We are actively prioritizing nearby feasible rescue partners."
            )
        elif urgency == "CRITICAL":
            if lang == "ta":
                return (
                    "🚨 மிக அவசர உணவு மீட்பு நிலை",
                    f"உங்கள் '{food_name}' நன்கொடைக்கு மிகக் குறைந்த மீட்பு நேரமே உள்ளது (~{remaining_minutes} நிமிடம்). அருகிலுள்ள NGO-க்கள் மற்றும் தன்னார்வலர்களுக்கு அவசர எச்சரிக்கை அனுப்பப்பட்டுள்ளது."
                )
            elif lang == "hi":
                return (
                    "🚨 अति गंभीर भोजन बचाव सूचना",
                    f"आपके '{food_name}' दान के लिए बहुत कम समय शेष है (~{remaining_minutes} मिनट)। तत्काल बचाव के लिए निकटतम भागीदारों को अलर्ट किया गया है।"
                )
            return (
                "🚨 Critical: Very Little Rescue Time Remaining",
                f"Critical: Your donation has very little estimated rescue time remaining (~{remaining_minutes}m). We are actively prioritizing fastest feasible rescue partners."
            )
        else: # RESCUE_WINDOW_ENDED
            if lang == "ta":
                return (
                    "மீட்பு காலக்கெடு முடிந்தது",
                    f"'{food_name}' நன்கொடைக்கான மதிப்பிடப்பட்ட மீட்பு காலக்கெடு முடிந்தது. மாற்று பாதுகாப்பு நடைமுறையை பரிசீலிக்கவும்."
                )
            elif lang == "hi":
                return (
                    "बचाव समय सीमा समाप्त",
                    f"'{food_name}' के लिए अनुमानित बचाव समय समाप्त हो चुका है। कृपया सुरक्षित निपटान की समीक्षा करें।"
                )
            return (
                "Estimated Rescue Window Ended",
                f"The estimated rescue window for '{food_name}' has ended. Normal dispatch has concluded."
            )

    elif role == "ngo":
        cat_str = f" [{food_category}]" if food_category else ""
        loc_str = pickup_address if pickup_address else dist_str
        adv_str = f" • Safety Advisory: {safety_advisory}" if safety_advisory else ""
        if urgency == "CRITICAL":
            if lang == "ta":
                return (
                    "🚨 மிக அவசர உணவு மீட்பு — உடனடி கவனம் தேவை",
                    f"{qty_str} '{food_name}'{cat_str} மீட்பு காலக்கெடுவின் முடிவை நெருங்குகிறது ({loc_str}, ~{remaining_minutes} நிமிடம் மீதம்){adv_str}. உடனடியாக ஏற்க பரிந்துரைக்கப்படுகிறது."
                )
            elif lang == "hi":
                return (
                    "🚨 अति गंभीर बचाव — तत्काल ध्यान आवश्यक",
                    f"{qty_str} '{food_name}'{cat_str} अपने अनुमानित बचाव समय के अंत के करीब है ({loc_str}, ~{remaining_minutes} मिनट शेष){adv_str}। त्वरित स्वीकृति अनुशंसित है।"
                )
            return (
                "🚨 Critical Rescue — Immediate Attention",
                f"{qty_str} of {food_name}{cat_str} are approaching the end of their estimated rescue window ({loc_str}, ~{remaining_minutes}m remaining){adv_str}. A feasible pickup/receipt is needed urgently."
            )
        else: # URGENT / APPROACHING / FRESH
            if lang == "ta":
                return (
                    "அவசர உணவு மீட்பு வாய்ப்பு",
                    f"{qty_str} '{food_name}'{cat_str} மீட்பு நிலையை எட்டியுள்ளது ({loc_str}, ~{remaining_minutes} நிமிடம் மீதம்){adv_str}. உங்கள் அமைப்பு இந்த உணவை ஏற்க சாத்தியமாக உள்ளது."
                )
            elif lang == "hi":
                return (
                    "நजदीक में तत्काल भोजन बचाव",
                    f"{qty_str} '{food_name}'{cat_str} समय-संवेदनशील हो रहा है ({loc_str}, ~{remaining_minutes} मिनट शेष){adv_str}। आपका संगठन इसे प्राप्त करने के लिए उपयुक्त है।"
                )
            return (
                "Urgent Food Rescue Nearby",
                f"{qty_str} of {food_name}{cat_str} available for rescue ({loc_str}, ~{remaining_minutes}m remaining){adv_str}. Your organization is eligible to receive this donation."
            )

    elif role == "volunteer":
        if urgency == "CRITICAL":
            if lang == "ta":
                return (
                    "🚨 மிக அவசர பிக்கப் பணி",
                    f"{qty_str} '{food_name}' உடனடி போக்குவரத்து தேவை ({dist_str}). வேகமான பிக்கப் சாத்தியமாக உள்ளது."
                )
            elif lang == "hi":
                return (
                    "🚨 अति गंभीर पिकअप कार्य",
                    f"{qty_str} '{food_name}' के लिए तत्काल परिवहन आवश्यक ({dist_str})। त्वरित पिकअप संभव है।"
                )
            return (
                "🚨 Critical Rescue — Immediate Pickup Required",
                f"Critical pickup needed: {qty_str} of {food_name} ({dist_str}). Estimated transit fits within rescue window."
            )
        else:
            if lang == "ta":
                return (
                    "அவசர உணவு பிக்கப் பணி",
                    f"அருகிலுள்ள அவசர உணவு மீட்பு: {qty_str} '{food_name}' ({dist_str})."
                )
            elif lang == "hi":
                return (
                    "तत्काल भोजन पिकअप कार्य",
                    f"नजदीकी तत्काल भोजन बचाव: {qty_str} '{food_name}' ({dist_str})।"
                )
            return (
                "Urgent Food Rescue Courier Task",
                f"Urgent food rescue nearby: {qty_str} of {food_name} ({dist_str}). Standard courier transit fits within window."
            )

    elif role == "admin":
        if lang == "ta":
            return (
                "🚨 நிர்வாக தலையீடு தேவை: அவசர உணவு மீட்பு",
                f"நன்கொடை #{food_name} ({qty_str}) மீட்பு காலக்கெடு முடிவுக்கு வருகிறது. NGO/தன்னார்வலர் இன்னும் ஏற்கவில்லை."
            )
        elif lang == "hi":
            return (
                "🚨 व्यवस्थापक हस्तक्षेप आवश्यक: गंभीर भोजन बचाव",
                f"दान #{food_name} ({qty_str}) की समय सीमा समाप्त होने वाली है। अभी तक किसी भी एनजीओ ने स्वीकार नहीं किया है।"
            )
        return (
            "🚨 Admin Intervention: Critical Rescue at Risk",
            f"Donation #{food_name} ({qty_str}) is approaching the end of rescue window (~{remaining_minutes}m remaining) with no NGO acceptance. Manual intervention recommended."
        )

    return ("Food Rescue Update", f"Update on {food_name} ({qty_str}).")


class ProactiveDispatchService:
    """
    Core orchestrator for Proactive Time-Critical Food Rescue Alert & NGO Dispatch.
    """

    @classmethod
    def evaluate_donation_urgency(
        cls,
        db: Session,
        donation: FoodDonation,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates authoritative remaining rescue window and urgency state using food rules and server time.
        Reuses calculate_advisory_rescue_window and food_knowledge_rules.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        prep_time = donation.preparation_time
        if prep_time and prep_time.tzinfo is None:
            prep_time = prep_time.replace(tzinfo=timezone.utc)

        # Parse storage history transitions if available
        storage_history = None
        if donation.storage_history_json:
            try:
                storage_history = json.loads(donation.storage_history_json)
            except Exception:
                storage_history = None

        is_custom_food = (donation.food_source == "CUSTOM") or (donation.custom_food_name is not None)
        assessment = evaluate_food_rescue_window(
            food_type=donation.food_type or donation.custom_food_name or donation.food_name,
            food_category=donation.food_category,
            prepared_at=prep_time or now,
            storage_method=donation.storage_method or "Room Temperature",
            storage_continuous=donation.storage_continuous if donation.storage_continuous is not None else True,
            storage_history=storage_history,
            packaging_status=donation.packaging_condition or "Covered",
            previously_served=donation.previously_served or "No",
            exposure_status=donation.exposure_status or "No",
            handling_status=donation.handling_status or "No",
            visual_condition_in=donation.ai_visual_condition or "GOOD",
            visible_spoilage_in=donation.ai_visible_spoilage,
            ai_confidence_in=donation.ai_confidence_score or 0.88,
            is_custom=is_custom_food,
            current_time=now,
        )

        remaining_minutes = assessment["remaining_minutes"]

        # If food rules calculation reached 0 but donation has an active remaining_minutes with future expiry
        if remaining_minutes <= 0 and donation.remaining_minutes and donation.remaining_minutes > 0:
            exp_t = donation.expiry_time
            if exp_t:
                if exp_t.tzinfo is None:
                    exp_t = exp_t.replace(tzinfo=timezone.utc)
                if exp_t > now:
                    remaining_minutes = donation.remaining_minutes
            else:
                remaining_minutes = donation.remaining_minutes

        # Authoritative Urgency Mapping
        if remaining_minutes <= THRESHOLD_CRITICAL_MINUTES:
            urgency_level = "RESCUE_WINDOW_ENDED"
        elif remaining_minutes <= THRESHOLD_URGENT_MINUTES:
            urgency_level = "CRITICAL"
        elif remaining_minutes <= THRESHOLD_APPROACHING_MINUTES:
            urgency_level = "URGENT"
        elif remaining_minutes <= THRESHOLD_FRESH_MINUTES:
            urgency_level = "APPROACHING"
        else:
            urgency_level = "FRESH"

        # Update donation record fields
        donation.remaining_minutes = remaining_minutes
        donation.rescue_urgency_level = urgency_level
        donation.urgency_level = urgency_level
        if assessment.get("estimated_window_end"):
            try:
                end_dt = datetime.fromisoformat(assessment["estimated_window_end"])
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                donation.estimated_window_end = end_dt
                donation.expiry_time = end_dt
            except Exception:
                pass

        if assessment.get("reasons"):
            donation.reasons_json = json.dumps(assessment["reasons"])

        # If window ended and status is still pending, update status appropriately
        if urgency_level == "RESCUE_WINDOW_ENDED" and donation.status == "pending":
            transition_donation_status(
                db, donation, "expired",
                changed_by_user_id=None,
                caller_role="system",
                remarks="RESCUE WINDOW ENDED: Advisory rescue deadline reached."
            )

        db.commit()
        db.refresh(donation)

        return {
            "donation_id": donation.id,
            "food_name": donation.food_name,
            "remaining_minutes": remaining_minutes,
            "urgency_level": urgency_level,
            "visual_condition": assessment["visual_condition"],
            "rule_coverage": assessment["rule_coverage"],
            "assessment": assessment,
        }

    @classmethod
    def find_and_rank_feasible_ngos(
        cls,
        db: Session,
        donation: FoodDonation,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Finds eligible NGOs, applies HARD GATES (verified, open, capacity, category, feasibility),
        and ranks candidates giving PRIORITY TO FEASIBILITY OVER PROXIMITY.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        remaining_minutes = donation.remaining_minutes or 120

        # Query active verified candidate NGOs
        ngos = db.query(NGO).filter(
            NGO.is_verified == True,
            NGO.is_available == True,
        ).all()

        candidates = []

        for ngo in ngos:
            # Check admin restriction
            if getattr(ngo, "admin_action_status", None) == "RESTRICTED":
                continue

            # 1. Distance Calculation
            dist = haversine_distance(
                donation.latitude, donation.longitude, ngo.latitude, ngo.longitude
            )
            if dist > 35.0: # Exclude extreme outliers
                continue

            # 2. Operating Hours Hard Gate
            is_open, open_status = is_ngo_open_now(ngo.operating_hours, now)
            if not is_open:
                continue

            # 3. Capacity Hard Gate
            current_cap = ngo.current_capacity if ngo.current_capacity is not None else (ngo.capacity or 100)
            if current_cap < donation.quantity:
                continue # Ineligible: cannot intake this donation quantity

            # 4. Demand & Category Match
            demand_score, is_demand_matched, demand_detail = calculate_demand_match_score(
                ngo.demand_requirements, donation.food_category, donation.quantity
            )

            # 5. Logistical Feasibility Engine (Feasibility > Proximity)
            # Transit time estimate: pickup preparation + distance * 3.0 min/km + intake
            # In Wave 3 / CRITICAL emergency situations, rapid response shelters expedite handling (5m prep / 5m intake)
            is_crit = (getattr(donation, "is_emergency", False) or getattr(donation, "rescue_urgency_level", None) == "CRITICAL")
            pickup_prep = 5.0 if is_crit else 15.0
            intake_time = 5.0 if is_crit else 10.0
            transit_time_min = max(6.0, dist * 3.0)
            feasibility = calculate_rescue_feasibility(
                remaining_window_minutes=remaining_minutes,
                estimated_pickup_minutes=pickup_prep,
                estimated_travel_minutes=transit_time_min,
                ngo_intake_minutes=intake_time,
            )

            # HARD GATE: If rescue is strictly unlikely/infeasible, EXCLUDE this NGO from priority alerts
            if not feasibility["is_feasible"] or remaining_minutes <= 0:
                continue

            # 6. Multi-Factor Scoring (Feasibility buffer + Travel time + Demand + Reliability)
            buffer_min = feasibility.get("remaining_buffer_minutes", 0)
            buffer_score = max(0.0, min(1.0, buffer_min / 60.0))
            dist_score = max(0.0, 1.0 - (dist / 25.0))
            receiving_reliability = (ngo.trust_score or 95.0) / 100.0

            # Composite ranking score
            composite_score = (
                (buffer_score * 0.35) +       # Feasibility safety buffer is top priority
                (dist_score * 0.25) +         # Proximity
                (demand_score * 0.20) +       # Beneficiary demand
                (receiving_reliability * 0.20) # Historical performance
            )

            candidates.append({
                "ngo_id": ngo.id,
                "user_id": ngo.user_id,
                "organization_name": ngo.organization_name,
                "distance_km": round(dist, 2),
                "transit_time_minutes": int(transit_time_min),
                "buffer_minutes": int(buffer_min),
                "feasibility_status": feasibility["feasibility_status"],
                "feasibility_label": feasibility["feasibility_label"],
                "demand_matched": is_demand_matched,
                "demand_detail": demand_detail,
                "reliability_score": ngo.trust_score or 95.0,
                "score": round(composite_score * 100, 1),
            })

        # Rank by composite score (highest first)
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    @classmethod
    def find_and_rank_feasible_volunteers(
        cls,
        db: Session,
        donation: FoodDonation,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Finds eligible community volunteers applying strict HARD GATES:
        1. Role == volunteer & is_active == True.
        2. Admin action status != RESTRICTED.
        3. Workload Hard Gate: active assignments count < 3.
        4. Carrying Capacity Hard Gate: vol.carrying_capacity >= donation.quantity (Capacity-feasible).
        5. Location Hard Gate: Distance <= 25.0 km (Location-feasible).
        6. Time & Logistics Feasibility: Pickup ETA + Travel + Intake < Remaining ERW (Time-feasible).
        
        Ranks candidates using multi-factor scoring (NEVER distance alone):
        Feasibility safety buffer (35%) + Distance (25%) + Reliability (25%) + Response speed (15%).
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        remaining_minutes = donation.remaining_minutes or 120

        volunteers = db.query(User).filter(
            User.role == "volunteer",
            User.is_active == True,
        ).all()

        candidates = []

        for vol in volunteers:
            # 1. Admin restriction check
            if getattr(vol, "admin_action_status", None) == "RESTRICTED":
                continue

            # 2. Workload Hard Gate: active tasks < 3
            active_count = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.volunteer_id == vol.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "collected", "en_route", "arrived", "in_transit"])
            ).count()
            if active_count >= 3:
                continue

            # 3. Carrying Capacity Hard Gate
            vol_cap = vol.carrying_capacity or 50
            if vol_cap < donation.quantity:
                continue

            # 4. Location Hard Gate: Distance <= 25.0 km
            dist = haversine_distance(
                donation.latitude, donation.longitude, vol.latitude, vol.longitude
            )
            if dist > 25.0:
                continue

            # 5. Time & Logistics Feasibility Hard Gate (Feasibility > Proximity)
            is_crit = (getattr(donation, "is_emergency", False) or getattr(donation, "rescue_urgency_level", None) == "CRITICAL")
            pickup_eta_min = max(4.0, dist * 2.5)
            travel_min = 10.0 if is_crit else 20.0
            intake_min = 5.0 if is_crit else 10.0
            feasibility = calculate_rescue_feasibility(
                remaining_window_minutes=remaining_minutes,
                estimated_pickup_minutes=pickup_eta_min,
                estimated_travel_minutes=travel_min,
                ngo_intake_minutes=intake_min,
            )

            if not feasibility["is_feasible"] or remaining_minutes <= 0:
                continue

            # 6. Multi-Factor Scoring (Never distance alone)
            buffer_min = feasibility.get("remaining_buffer_minutes", 0)
            buffer_score = max(0.0, min(1.0, buffer_min / 60.0))
            dist_score = max(0.0, 1.0 - (dist / 20.0))
            reliability_score = (vol.reliability_score or 95.0) / 100.0
            resp_sec = vol.avg_response_time_seconds or 180.0
            response_speed = max(0.2, min(1.0, 1.0 - (resp_sec / 600.0)))

            composite_score = (
                (buffer_score * 0.35) +
                (dist_score * 0.25) +
                (reliability_score * 0.25) +
                (response_speed * 0.15)
            )

            candidates.append({
                "volunteer_id": vol.id,
                "user_id": vol.id,
                "name": vol.name,
                "phone": vol.phone,
                "vehicle_type": vol.vehicle_type or "bike",
                "carrying_capacity": vol_cap,
                "distance_km": round(dist, 2),
                "pickup_eta_minutes": int(pickup_eta_min),
                "buffer_minutes": int(buffer_min),
                "feasibility_status": feasibility["feasibility_status"],
                "feasibility_label": feasibility["feasibility_label"],
                "reliability_score": vol.reliability_score or 95.0,
                "active_tasks": active_count,
                "score": round(composite_score * 100, 1),
            })

        # Rank by composite score (highest first)
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    @classmethod
    def dispatch_proactive_alerts(
        cls,
        db: Session,
        donation: FoodDonation,
        reference_time: Optional[datetime] = None,
        force_dispatch: bool = False,
    ) -> Dict[str, Any]:
        """
        Three-Wave Proactive Dispatch Engine:
        - Wave 1 (NGO Self-Pickup): Approaching urgency, nearest verified NGOs, short cooldown.
        - Wave 2 (Volunteer Support): Expands search to feasible community volunteer couriers.
        - Wave 3 (Critical Emergency): Simultaneous broadcast to emergency shelters, on-call volunteers, and Admin escalation.
        
        Strict Rules:
        - Every wave checks donation state and recalculates live ERW.
        - Avoids duplicate active offers.
        - Respects cooldown.
        - Records wave_number, offer score, and timing.
        - Stops immediately if donation is already accepted for self-pickup.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Live ERW Re-evaluation at Execution Time
        eval_result = cls.evaluate_donation_urgency(db, donation, reference_time=now)
        urgency = eval_result["urgency_level"]
        remaining_minutes = eval_result["remaining_minutes"]

        if urgency == "RESCUE_WINDOW_ENDED" or remaining_minutes <= 0 or donation.status == "expired":
            # Cancel outstanding offers
            db.query(MatchOffer).filter(
                MatchOffer.donation_id == donation.id,
                MatchOffer.status == "offered"
            ).update({"status": "cancelled", "responded_at": now})
            if donation.status == "pending":
                transition_donation_status(
                    db, donation, "expired",
                    changed_by_user_id=None,
                    caller_role="system",
                    remarks="RESCUE WINDOW ENDED: Advisory deadline reached. Dispatch halted."
                )
                create_event_notification(
                    db=db,
                    user_id=donation.donor_id,
                    event_type="RESCUE_EXPIRED",
                    donation_id=donation.id,
                )
            db.commit()
            return {
                "status": "WINDOW_ENDED",
                "reason": "Rescue window has ended. Dispatch halted.",
                "donation_id": donation.id,
            }

        # 2. Donation State Checks
        if donation.status not in ["pending", "accepted"]:
            return {
                "status": "SKIPPED",
                "reason": f"Donation status is '{donation.status}', no dispatch required.",
                "donation_id": donation.id,
            }

        if donation.status == "accepted":
            if donation.pickup_mode == "self_pickup":
                return {
                    "status": "SKIPPED",
                    "reason": "Donation accepted for NGO self-pickup. Courier dispatch unnecessary.",
                    "donation_id": donation.id,
                }
            if donation.assigned_volunteer_id is not None:
                return {
                    "status": "SKIPPED",
                    "reason": "Volunteer courier already assigned.",
                    "donation_id": donation.id,
                }

        # 3. Check Deduplication & Cooldown
        last_urgency = donation.last_alerted_urgency
        last_alerted_at = donation.last_alerted_at
        if last_alerted_at and last_alerted_at.tzinfo is None:
            last_alerted_at = last_alerted_at.replace(tzinfo=timezone.utc)

        state_increased = (
            last_urgency is None
            or URGENCY_ORDER.get(urgency, 0) > URGENCY_ORDER.get(last_urgency, 0)
        )

        cooldown_elapsed = True
        if last_alerted_at:
            minutes_since_alert = (now - last_alerted_at).total_seconds() / 60.0
            cooldown_elapsed = minutes_since_alert >= ALERT_COOLDOWN_MINUTES

        if not force_dispatch and not state_increased and not cooldown_elapsed:
            return {
                "status": "COOLDOWN_ACTIVE",
                "reason": f"Alert deduplication active for state '{urgency}'. Last alerted at {last_alerted_at}.",
                "donation_id": donation.id,
            }

        # 4. If FRESH or normal operations, no urgent wave dispatch required
        if urgency == "FRESH":
            donation.last_alerted_urgency = "FRESH"
            donation.last_alerted_at = now
            db.commit()
            return {
                "status": "NORMAL_OPERATIONS",
                "urgency": "FRESH",
                "donation_id": donation.id,
            }

        # 5. Determine Current Wave
        current_wave = (donation.current_alert_wave or 0) + 1
        if urgency == "CRITICAL" and current_wave < 3:
            current_wave = 3  # Immediate jump to Wave 3 for critical emergency
        elif donation.status == "accepted" and donation.pickup_mode == "volunteer_dispatch":
            current_wave = max(2, current_wave)  # Direct to Wave 2 for volunteer courier support

        # Timeout settings
        timeout_minutes = WAVE_TIMEOUT_CRITICAL_MINUTES if (urgency == "CRITICAL" or current_wave >= 3) else WAVE_TIMEOUT_URGENT_MINUTES
        wave_timeout_at = now + timedelta(minutes=timeout_minutes)

        # Active offers set to prevent duplicate active offers
        active_candidate_ids = {
            row[0] for row in db.query(MatchOffer.candidate_id).filter(
                MatchOffer.donation_id == donation.id,
                MatchOffer.status == "offered"
            ).all()
        }

        all_offered_candidate_ids = {
            row[0] for row in db.query(MatchOffer.candidate_id).filter(
                MatchOffer.donation_id == donation.id
            ).all()
        }

        # Candidate ranking
        ranked_ngos = cls.find_and_rank_feasible_ngos(db, donation, reference_time=now)
        ranked_vols = cls.find_and_rank_feasible_volunteers(db, donation, reference_time=now)

        selected_ngos = []
        selected_vols = []

        # ── WAVE 1: NGO Self-Pickup ──────────────────────────────────────────
        if current_wave == 1:
            fresh_ngos = [c for c in ranked_ngos if c["user_id"] not in all_offered_candidate_ids]
            selected_ngos = fresh_ngos[:WAVE_1_SIZE]
            if not selected_ngos and ranked_ngos:
                selected_ngos = [c for c in ranked_ngos if c["user_id"] not in active_candidate_ids][:WAVE_1_SIZE]

            if not selected_ngos:
                # No feasible NGO for Wave 1 self-pickup -> advance directly to Wave 2 volunteer search
                current_wave = 2

        # ── WAVE 2: Volunteer Support & Expanded Courier Dispatch ────────────
        if current_wave == 2:
            fresh_vols = [v for v in ranked_vols if v["user_id"] not in active_candidate_ids]
            selected_vols = fresh_vols[:WAVE_2_SIZE]

            # If donation is still pending (no NGO accepted yet), also expand search to next batch of candidate NGOs
            if donation.status == "pending":
                fresh_ngos = [c for c in ranked_ngos if c["user_id"] not in all_offered_candidate_ids]
                selected_ngos = fresh_ngos[:WAVE_1_SIZE]
                if not selected_ngos and ranked_ngos:
                    selected_ngos = [c for c in ranked_ngos if c["user_id"] not in active_candidate_ids][:WAVE_1_SIZE]

        # ── WAVE 3: Critical Emergency Broadcast ──────────────────────────────
        if current_wave >= 3:
            donation.is_emergency = True
            selected_ngos = [c for c in ranked_ngos if c["user_id"] not in active_candidate_ids][:WAVE_1_SIZE]
            selected_vols = [v for v in ranked_vols if v["user_id"] not in active_candidate_ids][:WAVE_2_SIZE]

            # Immediate Admin Escalation for Wave 3 critical rescue
            cls._escalate_to_admin(
                db,
                donation,
                reason=f"Wave {current_wave} Critical Emergency dispatch active ({remaining_minutes}m rescue window remaining).",
                remaining_minutes=remaining_minutes,
            )

        if not selected_ngos and not selected_vols:
            # All candidates exhausted -> Escalate to Admin
            cls._escalate_to_admin(
                db,
                donation,
                reason=f"All candidate NGOs and volunteers exhausted with no active offers. Admin intervention required.",
                remaining_minutes=remaining_minutes,
            )
            return {
                "status": "ALL_CANDIDATES_EXHAUSTED",
                "urgency": urgency,
                "wave": current_wave,
                "donation_id": donation.id,
            }

        # 6. Dispatch Notifications & MatchOffers
        approx_area = _extract_approximate_area(donation.pickup_address)
        alerted_ngo_ids = []
        alerted_vol_ids = []

        # Dispatch to Selected NGOs
        for cand in selected_ngos:
            if cand["user_id"] in active_candidate_ids:
                continue

            offer = MatchOffer(
                donation_id=donation.id,
                candidate_id=cand["user_id"],
                candidate_type="ngo",
                score=cand["score"],
                status="offered",
                wave_number=current_wave,
                offered_at=now,
                expires_at=wave_timeout_at,
            )
            db.add(offer)

            ngo_user = db.query(User).filter(User.id == cand["user_id"]).first()
            user_lang = getattr(ngo_user, "preferred_language", "en") if ngo_user else "en"

            safety_adv = donation.ai_safety_disclaimer or (f"Visual condition: {donation.ai_visual_condition}" if donation.ai_visual_condition else None)
            title, msg = format_proactive_alert_message(
                role="ngo",
                urgency=urgency,
                language=user_lang,
                food_name=donation.food_name,
                quantity=donation.quantity,
                quantity_unit=donation.quantity_unit,
                distance_km=cand["distance_km"],
                area_name=approx_area,
                remaining_minutes=remaining_minutes,
                food_category=donation.food_category,
                pickup_address=donation.pickup_address,
                safety_advisory=safety_adv,
            )

            create_event_notification(
                db=db,
                user_id=cand["user_id"],
                event_type="OFFER_RECEIVED",
                donation_id=donation.id,
                lang=user_lang,
                extra_message=msg,
            )
            alerted_ngo_ids.append(cand.get("ngo_id", cand["user_id"]))

        # Dispatch to Selected Volunteers
        for vol_cand in selected_vols:
            if vol_cand["user_id"] in active_candidate_ids:
                continue

            offer = MatchOffer(
                donation_id=donation.id,
                candidate_id=vol_cand["user_id"],
                candidate_type="volunteer",
                score=vol_cand["score"],
                status="offered",
                wave_number=current_wave,
                offered_at=now,
                expires_at=wave_timeout_at,
            )
            db.add(offer)

            vol_user = db.query(User).filter(User.id == vol_cand["user_id"]).first()
            user_lang = getattr(vol_user, "preferred_language", "en") if vol_user else "en"

            title, msg = format_proactive_alert_message(
                role="volunteer",
                urgency=urgency,
                language=user_lang,
                food_name=donation.food_name,
                quantity=donation.quantity,
                quantity_unit=donation.quantity_unit,
                distance_km=vol_cand["distance_km"],
                area_name=approx_area,
                remaining_minutes=remaining_minutes,
            )

            create_event_notification(
                db=db,
                user_id=vol_cand["user_id"],
                event_type="OFFER_RECEIVED",
                donation_id=donation.id,
                lang=user_lang,
                extra_message=msg,
            )
            alerted_vol_ids.append(vol_cand["volunteer_id"])

        # 7. Notify Donor with Proactive Reassurance
        donor_user = db.query(User).filter(User.id == donation.donor_id).first()
        donor_lang = getattr(donor_user, "preferred_language", "en") if donor_user else "en"
        donor_title, donor_msg = format_proactive_alert_message(
            role="donor",
            urgency=urgency,
            language=donor_lang,
            food_name=donation.food_name,
            quantity=donation.quantity,
            quantity_unit=donation.quantity_unit,
            remaining_minutes=remaining_minutes,
        )
        create_event_notification(
            db=db,
            user_id=donation.donor_id,
            event_type="WAVE_ESCALATED" if current_wave > 1 else "DONATION_CREATED",
            donation_id=donation.id,
            lang=donor_lang,
            extra_message=donor_msg,
            extra_title=donor_title,
        )

        # 8. Update donation wave metadata
        donation.last_alerted_urgency = urgency
        donation.last_alerted_at = now
        donation.current_alert_wave = current_wave
        donation.wave_timeout_at = wave_timeout_at

        # Append alert event to alert history
        history_list = []
        if donation.alert_history_json:
            try:
                history_list = json.loads(donation.alert_history_json)
            except Exception:
                history_list = []

        history_list.append({
            "wave": current_wave,
            "urgency": urgency,
            "timestamp": now.isoformat(),
            "ngo_count": len(selected_ngos),
            "volunteer_count": len(selected_vols),
            "alerted_ngo_ids": alerted_ngo_ids,
            "alerted_volunteer_ids": alerted_vol_ids,
            "timeout_at": wave_timeout_at.isoformat(),
        })
        donation.alert_history_json = json.dumps(history_list)

        db.commit()
        db.refresh(donation)

        logger.info(
            f"[ProactiveDispatch] Donation #{donation.id} ({urgency}): Wave {current_wave} dispatched to "
            f"{len(selected_ngos)} NGOs and {len(selected_vols)} Volunteers (Timeout in {timeout_minutes}m)."
        )

        return {
            "status": "DISPATCHED",
            "donation_id": donation.id,
            "urgency": urgency,
            "wave": current_wave,
            "alerted_ngo_count": len(selected_ngos),
            "alerted_volunteer_count": len(selected_vols),
            "alerted_ngos": selected_ngos,
            "alerted_volunteers": selected_vols,
            "timeout_minutes": timeout_minutes,
        }

    @classmethod
    def check_and_escalate_unresponsive_waves(
        cls,
        db: Session,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scans pending and unassigned accepted donations with active alert waves.
        If a wave has timed out without acceptance:
        - Wave 1 times out -> Triggers Wave 2 (Volunteer Support).
        - Wave 2 times out -> Triggers Wave 3 (Critical Emergency).
        - Wave 3 times out -> Escalates directly to Admin.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        active_donations = db.query(FoodDonation).filter(
            FoodDonation.status.in_(["pending", "accepted"]),
            FoodDonation.current_alert_wave > 0,
            FoodDonation.wave_timeout_at.isnot(None),
        ).all()

        escalated_results = []

        for donation in active_donations:
            # Stop if accepted for self-pickup
            if donation.status == "accepted" and donation.pickup_mode == "self_pickup":
                continue
            # Stop if volunteer already assigned
            if donation.status == "accepted" and donation.assigned_volunteer_id is not None:
                continue

            timeout_at = donation.wave_timeout_at
            if timeout_at and timeout_at.tzinfo is None:
                timeout_at = timeout_at.replace(tzinfo=timezone.utc)

            if timeout_at and now >= timeout_at:
                logger.info(
                    f"[ProactiveDispatch] Donation #{donation.id} Wave {donation.current_alert_wave} timed out at {timeout_at}. Escalating."
                )
                # Mark timed-out wave offers as expired
                db.query(MatchOffer).filter(
                    MatchOffer.donation_id == donation.id,
                    MatchOffer.status == "offered",
                    MatchOffer.wave_number == donation.current_alert_wave
                ).update({"status": "expired"})
                db.commit()

                # Re-evaluate ERW at execution time
                eval_res = cls.evaluate_donation_urgency(db, donation, reference_time=now)
                if eval_res["urgency_level"] == "RESCUE_WINDOW_ENDED" or donation.status == "expired":
                    continue

                # Trigger next wave
                dispatch_res = cls.dispatch_proactive_alerts(
                    db, donation, reference_time=now, force_dispatch=True
                )
                escalated_results.append({
                    "donation_id": donation.id,
                    "previous_wave": donation.current_alert_wave - 1,
                    "new_wave": donation.current_alert_wave,
                    "dispatch_result": dispatch_res,
                })

        return escalated_results

    @classmethod
    def process_atomic_ngo_acceptance(
        cls,
        db: Session,
        donation_id: int,
        ngo_user_id: int,
        reference_time: Optional[datetime] = None,
        pickup_mode: str = "volunteer_dispatch",
        offer_id: Optional[int] = None,
        caller_role: str = "ngo",
    ) -> Dict[str, Any]:
        """
        Atomic acceptance lock for NGOs.
        Guarantees that only ONE NGO can accept. Subsequent attempts receive 409 Conflict.
        Verifies authenticated NGO and verifies that offer belongs to this NGO.
        Revokes all other outstanding wave invitations.
        If pickup_mode is 'self_pickup', marks self-pickup flow and does NOT create volunteer assignments.
        If pickup_mode is 'volunteer_dispatch', activates Wave 2 courier dispatch.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Fetch and verify authenticated NGO entity
        ngo = db.query(NGO).filter(NGO.user_id == ngo_user_id).first()
        if not ngo and caller_role == "admin":
            ngo = db.query(NGO).filter(NGO.is_verified == True).first()
        if not ngo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NGO profile not found for current user."
            )
        if not ngo.is_verified and caller_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your NGO account is not verified. Only verified NGOs can accept donations."
            )
        if getattr(ngo, "admin_action_status", None) == "RESTRICTED" and caller_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your NGO account is currently restricted."
            )

        # 2. Verify offer belongs to this NGO
        winning_offer = None
        if offer_id is not None:
            offer = db.query(MatchOffer).filter(MatchOffer.id == offer_id).first()
            if not offer or offer.donation_id != donation_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified offer not found for this donation."
                )
            if offer.candidate_type != "ngo":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This offer is not for an NGO."
                )
            if caller_role != "admin" and offer.candidate_id != ngo_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This offer does not belong to your organization."
                )
            if offer.status not in ["offered", "accepted"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Offer is no longer active (status: '{offer.status}')."
                )
            winning_offer = offer
            if caller_role == "admin" and offer.candidate_id:
                admin_ngo = db.query(NGO).filter(NGO.user_id == offer.candidate_id).first()
                if admin_ngo:
                    ngo = admin_ngo
        else:
            my_offer = db.query(MatchOffer).filter(
                MatchOffer.donation_id == donation_id,
                MatchOffer.candidate_id == ngo_user_id,
                MatchOffer.candidate_type == "ngo",
                MatchOffer.status == "offered"
            ).first()

            active_other_offers = db.query(MatchOffer).filter(
                MatchOffer.donation_id == donation_id,
                MatchOffer.status == "offered",
                MatchOffer.candidate_type == "ngo",
                MatchOffer.candidate_id != ngo_user_id
            ).count()

            if active_other_offers > 0 and not my_offer and caller_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This donation is currently under active offer to other shortlisted organizations."
                )
            winning_offer = my_offer

        # 3. Acquire atomic database lock on the donation
        donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found."
            )

        # 4. Check if rescue window ended (recalculate ERW)
        cls.evaluate_donation_urgency(db, donation, reference_time=now)
        if donation.status == "expired":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Estimated rescue window has ended for this donation. Acceptance disabled."
            )
        elif donation.remaining_minutes is not None and donation.remaining_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estimated rescue window has ended for this donation. Acceptance disabled."
            )

        # 5. Check if already accepted or cancelled (verify donation still available)
        if donation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This donation has already been accepted by another organization or is no longer available (status: '{donation.status}')."
            )

        # 6. Check NGO capacity
        if ngo.current_capacity is not None and ngo.current_capacity < donation.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient capacity ({ngo.current_capacity} meals available, {donation.quantity} required)."
            )

        # 7. Apply Atomic State Transition
        donation.assigned_ngo_id = ngo.id
        donation.pickup_mode = pickup_mode
        if ngo.current_capacity is not None:
            ngo.current_capacity = max(0.0, ngo.current_capacity - donation.quantity)

        pickup_label = "Self-Pickup by NGO" if pickup_mode == "self_pickup" else "Volunteer Courier Dispatch Requested"
        transition_donation_status(
            db, donation, "accepted",
            changed_by_user_id=ngo_user_id,
            caller_role=caller_role,
            remarks=f"Accepted by NGO: {ngo.organization_name} ({pickup_label})."
        )
        if pickup_mode == "self_pickup":
            log_rescue_operation(
                db=db,
                action="self-pickup selected",
                donation_id=donation.id,
                user_id=ngo_user_id,
                remarks="Self-pickup selected by NGO",
                details=f"NGO #{ngo.id} ({ngo.organization_name}) selected self-pickup for donation #{donation.id}",
            )

        # 8. Accept offer and record response time
        if not winning_offer:
            winning_offer = db.query(MatchOffer).filter(
                MatchOffer.donation_id == donation.id,
                MatchOffer.candidate_id == ngo_user_id,
                MatchOffer.candidate_type == "ngo"
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
            # Create acceptance offer record if accepted directly from feed
            winning_offer = MatchOffer(
                donation_id=donation.id,
                candidate_id=ngo_user_id,
                candidate_type="ngo",
                score=100.0,
                status="accepted",
                wave_number=donation.current_alert_wave or 1,
                offered_at=now,
                responded_at=now,
                response_time_seconds=0.0,
            )
            db.add(winning_offer)

        # 8. Cancel all other outstanding offers for this donation
        other_offers = db.query(MatchOffer).filter(
            MatchOffer.donation_id == donation.id,
            MatchOffer.id != (winning_offer.id if winning_offer else 0),
            MatchOffer.status == "offered"
        ).all()
        for off in other_offers:
            off.status = "cancelled"
            off.responded_at = now

        # 9. Notify Donor
        donor = db.query(User).filter(User.id == donation.donor_id).first()
        donor_lang = getattr(donor, "preferred_language", "en") if donor else "en"
        create_event_notification(
            db=db,
            user_id=donation.donor_id,
            event_type="OFFER_ACCEPTED",
            donation_id=donation.id,
            lang=donor_lang,
            extra_message=f"'{donation.food_name}' has been accepted by '{ngo.organization_name}' ({pickup_label}).",
        )

        log_audit_event(
            db,
            action="donation_accepted",
            user_id=ngo_user_id,
            resource_type="donation",
            resource_id=donation.id,
            status_code="success",
            details=f"NGO '{ngo.organization_name}' accepted donation #{donation.id} ({pickup_label})."
        )

        db.commit()
        db.refresh(donation)

        # 10. If volunteer courier requested, trigger Wave 2 courier dispatch
        if pickup_mode == "volunteer_dispatch":
            cls.dispatch_proactive_alerts(db, donation, reference_time=now, force_dispatch=True)

        logger.info(
            f"[ProactiveDispatch] Donation #{donation.id} ATOMICALLY ACCEPTED by NGO #{ngo.id} ({ngo.organization_name}) [{pickup_label}]."
        )

        return {
            "status": "ACCEPTED",
            "donation_id": donation.id,
            "assigned_ngo_id": ngo.id,
            "organization_name": ngo.organization_name,
            "pickup_mode": pickup_mode,
            "accepted_at": now.isoformat(),
            "remaining_minutes": donation.remaining_minutes,
        }

    @classmethod
    def _escalate_to_admin(
        cls,
        db: Session,
        donation: FoodDonation,
        reason: str,
        remaining_minutes: int,
    ) -> None:
        """
        Creates an admin critical intervention alert when automated matching cannot complete in time.
        """
        donation.is_emergency = True
        donation.escalated_at = _utcnow()

        # Check if intervention report already exists
        existing_report = db.query(RescueIssueReport).filter(
            RescueIssueReport.donation_id == donation.id,
            RescueIssueReport.category == "other",
            RescueIssueReport.status.in_(["OPEN", "IN_PROGRESS", "UNDER_REVIEW"])
        ).first()

        if not existing_report:
            report = RescueIssueReport(
                donation_id=donation.id,
                reporter_id=donation.donor_id,
                reporter_role="system",
                category="other",
                severity="CRITICAL",
                description=f"CRITICAL RESCUE AT RISK: {reason} (~{remaining_minutes}m rescue window remaining).",
                status="OPEN",
            )
            db.add(report)

        # Alert all Admins
        admins = db.query(User).filter(User.role == "admin").all()
        for admin in admins:
            create_notification(
                db=db,
                user_id=admin.id,
                title="🚨 CRITICAL RESCUE AT RISK: Admin Escalation",
                message=f"Donation #{donation.id} ('{donation.food_name}', {donation.quantity} {donation.quantity_unit}) has {remaining_minutes}m remaining with no accepted NGO. Immediate intervention required.",
                type="emergency",
                related_donation_id=donation.id,
            )

        db.commit()


# ── Background Urgency Monitoring Thread Loop ────────────────────────────────
class BackgroundUrgencyMonitor:
    """
    Continuous server-side background worker that monitors all active food donations
    and triggers automated proactive dispatches and wave escalations.
    """
    _running: bool = False
    _thread: Optional[threading.Thread] = None
    _interval_seconds: int = 60

    @classmethod
    def start(cls, interval_seconds: int = 60):
        if cls._running:
            return
        cls._running = True
        cls._interval_seconds = interval_seconds
        cls._thread = threading.Thread(target=cls._monitor_loop, daemon=True, name="ProactiveUrgencyMonitor")
        cls._thread.start()
        logger.info(f"[ProactiveUrgencyMonitor] Background monitor thread started (Interval: {interval_seconds}s).")

    @classmethod
    def stop(cls):
        cls._running = False
        logger.info("[ProactiveUrgencyMonitor] Background monitor thread stopped.")

    @classmethod
    def _monitor_loop(cls):
        while cls._running:
            try:
                cls.run_cycle()
            except Exception as e:
                logger.error(f"[ProactiveUrgencyMonitor] Error in monitoring cycle: {e}")
            time.sleep(cls._interval_seconds)

    @classmethod
    def run_cycle(cls, reference_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Executes a single complete monitoring and dispatch cycle across all active donations.
        """
        db = SessionLocal()
        now = reference_time or _utcnow()
        try:
            active_donations = db.query(FoodDonation).filter(
                FoodDonation.status.in_(["pending", "accepted"])
            ).all()

            evaluated_count = 0
            dispatched_count = 0

            for donation in active_donations:
                evaluated_count += 1
                res = ProactiveDispatchService.dispatch_proactive_alerts(db, donation, reference_time=now)
                if res.get("status") in ["DISPATCHED", "COOLDOWN_ACTIVE"]:
                    dispatched_count += 1

            # Check wave timeouts
            escalations = ProactiveDispatchService.check_and_escalate_unresponsive_waves(db, reference_time=now)

            # Continuous Feasibility & Telemetry Staleness Monitoring for Active Rescues
            from app.services.rematching_service import rematching_service
            active_rescues = db.query(FoodDonation).filter(
                FoodDonation.status.in_([
                    "volunteer_assigned", "pickup_en_route", "en_route",
                    "arrived_at_donor", "arrived", "collected", "in_transit"
                ]),
                FoodDonation.assigned_volunteer_id.isnot(None)
            ).all()

            rematches_triggered = 0
            for rescue in active_rescues:
                health = rematching_service.verify_active_assignment_health(db, rescue, reference_time=now)
                if health.get("requires_rematch"):
                    rematch_res = rematching_service.attempt_dynamic_rematch(
                        db=db,
                        donation=rescue,
                        trigger=health.get("trigger", "HEALTH_CHECK_FAILED"),
                        reason=health.get("reason", "Automated feasibility/telemetry check triggered rematch")
                    )
                    if rematch_res.get("status") == "REMATCHED":
                        rematches_triggered += 1

            return {
                "status": "SUCCESS",
                "timestamp": now.isoformat(),
                "active_donations_evaluated": evaluated_count,
                "dispatches_triggered": dispatched_count,
                "escalations_count": len(escalations),
                "rematches_triggered": rematches_triggered,
            }
        finally:
            db.close()
