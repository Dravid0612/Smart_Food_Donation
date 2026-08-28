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
)
from app.services.food_rescue_window_service import (
    evaluate_food_rescue_window,
    calculate_rescue_feasibility,
)
from app.services.notification_service import create_notification
from app.services.recommendation_service import (
    haversine_distance,
    is_ngo_open_now,
    calculate_demand_match_score,
)

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
) -> Tuple[str, str]:
    """
    Generates natural, non-machine-like trilingual alerts for Donor, NGO, Volunteer, and Admin.
    """
    lang = (language or "en").lower()
    qty_str = f"{int(quantity) if quantity.is_integer() else quantity:.1f} {quantity_unit}"
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
        if urgency == "CRITICAL":
            if lang == "ta":
                return (
                    "🚨 மிக அவசர உணவு மீட்பு — உடனடி கவனம் தேவை",
                    f"{qty_str} '{food_name}' மீட்பு காலக்கெடுவின் முடிவை நெருங்குகிறது ({dist_str}, ~{remaining_minutes} நிமிடம் மீதம்). உடனடியாக ஏற்க பரிந்துரைக்கப்படுகிறது."
                )
            elif lang == "hi":
                return (
                    "🚨 अति गंभीर बचाव — तत्काल ध्यान आवश्यक",
                    f"{qty_str} '{food_name}' अपने अनुमानित बचाव समय के अंत के करीब है ({dist_str}, ~{remaining_minutes} मिनट शेष)। त्वरित स्वीकृति अनुशंसित है।"
                )
            return (
                "🚨 Critical Rescue — Immediate Attention",
                f"{qty_str} of {food_name} are approaching the end of their estimated rescue window ({dist_str}, ~{remaining_minutes}m remaining). A feasible pickup/receipt is needed urgently."
            )
        else: # URGENT
            if lang == "ta":
                return (
                    "அவசர உணவு மீட்பு வாய்ப்பு",
                    f"{qty_str} '{food_name}' அவசர மீட்பு நிலையை எட்டியுள்ளது ({dist_str}). உங்கள் அமைப்பு இந்த உணவை ஏற்க சாத்தியமாக உள்ளது."
                )
            elif lang == "hi":
                return (
                    "नजदीक में तत्काल भोजन बचाव",
                    f"{qty_str} '{food_name}' समय-संवेदनशील हो रहा है ({dist_str})। आपका संगठन इसे प्राप्त करने के लिए उपयुक्त है।"
                )
            return (
                "Urgent Food Rescue Nearby",
                f"{qty_str} of {food_name} are becoming time-critical ({dist_str}, ~{remaining_minutes}m remaining). Your organization is eligible to receive this donation."
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
            donation.status = "expired"
            history = DonationHistory(
                donation_id=donation.id,
                old_status="pending",
                new_status="expired",
                changed_by=None,
                remarks="RESCUE WINDOW ENDED: Advisory rescue deadline reached."
            )
            db.add(history)

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
            # Transit time estimate: 15 min pickup preparation + distance * 3.0 min/km + 10 min intake
            transit_time_min = max(8.0, dist * 3.0)
            feasibility = calculate_rescue_feasibility(
                remaining_window_minutes=remaining_minutes,
                estimated_pickup_minutes=15.0,
                estimated_travel_minutes=transit_time_min,
                ngo_intake_minutes=10.0,
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
    def dispatch_proactive_alerts(
        cls,
        db: Session,
        donation: FoodDonation,
        reference_time: Optional[datetime] = None,
        force_dispatch: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates urgency and performs targeted multi-wave alerting with deduplication and cooldown.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Evaluate urgency
        eval_result = cls.evaluate_donation_urgency(db, donation, reference_time=now)
        urgency = eval_result["urgency_level"]
        remaining_minutes = eval_result["remaining_minutes"]

        if urgency == "RESCUE_WINDOW_ENDED":
            # Cancel outstanding offers
            db.query(MatchOffer).filter(
                MatchOffer.donation_id == donation.id,
                MatchOffer.status == "offered"
            ).update({"status": "cancelled"})
            db.commit()
            return {
                "status": "WINDOW_ENDED",
                "reason": "Rescue window has ended. Dispatch halted.",
                "donation_id": donation.id,
            }

        if donation.status not in ["pending", "accepted"]:
            return {
                "status": "SKIPPED",
                "reason": f"Donation status is '{donation.status}', no dispatch required.",
                "donation_id": donation.id,
            }

        # 2. Check Deduplication & Cooldown
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

        # 3. If FRESH or normal operations, no mass alert required
        if urgency == "FRESH":
            donation.last_alerted_urgency = "FRESH"
            donation.last_alerted_at = now
            db.commit()
            return {
                "status": "NORMAL_OPERATIONS",
                "urgency": "FRESH",
                "donation_id": donation.id,
            }

        # 4. Find ranked feasible NGOs
        ranked_ngos = cls.find_and_rank_feasible_ngos(db, donation, reference_time=now)

        if not ranked_ngos:
            # No feasible NGO found -> If CRITICAL or URGENT, escalate to Admin!
            if urgency in ["URGENT", "CRITICAL"]:
                cls._escalate_to_admin(
                    db,
                    donation,
                    reason=f"No feasible NGOs available for {urgency} rescue ({remaining_minutes}m remaining).",
                    remaining_minutes=remaining_minutes,
                )
            return {
                "status": "NO_FEASIBLE_NGOS",
                "urgency": urgency,
                "donation_id": donation.id,
                "reason": "No NGOs met feasibility and capacity hard gates.",
            }

        # 5. Multi-Wave Selection
        current_wave = (donation.current_alert_wave or 0) + 1
        wave_size = WAVE_1_SIZE if current_wave == 1 else WAVE_2_SIZE

        # Select candidates not previously offered in earlier waves
        previous_candidate_user_ids = {
            row[0] for row in db.query(MatchOffer.candidate_id).filter(
                MatchOffer.donation_id == donation.id
            ).all()
        }

        fresh_candidates = [
            c for c in ranked_ngos if c["user_id"] not in previous_candidate_user_ids
        ]

        if not fresh_candidates and current_wave > 1:
            # All candidates exhausted -> Escalate to Admin
            cls._escalate_to_admin(
                db,
                donation,
                reason=f"All {len(ranked_ngos)} candidate NGOs contacted with no response. Escalation required.",
                remaining_minutes=remaining_minutes,
            )
            return {
                "status": "ALL_CANDIDATES_EXHAUSTED",
                "urgency": urgency,
                "donation_id": donation.id,
            }

        selected_candidates = fresh_candidates[:wave_size]
        if not selected_candidates:
            selected_candidates = ranked_ngos[:wave_size] # Fallback to top ranked if needed

        # 6. Dispatch Notifications & Match Offers to Selected Wave
        approx_area = _extract_approximate_area(donation.pickup_address)
        timeout_minutes = WAVE_TIMEOUT_CRITICAL_MINUTES if urgency == "CRITICAL" else WAVE_TIMEOUT_URGENT_MINUTES
        wave_timeout_at = now + timedelta(minutes=timeout_minutes)

        alerted_ngo_ids = []
        for cand in selected_candidates:
            # Create MatchOffer
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

            # Determine NGO preferred language (if stored, otherwise English)
            ngo_user = db.query(User).filter(User.id == cand["user_id"]).first()
            user_lang = getattr(ngo_user, "preferred_language", "en") if ngo_user else "en"

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
            )

            create_notification(
                db=db,
                user_id=cand["user_id"],
                title=title,
                message=msg,
                type="emergency" if urgency == "CRITICAL" else "alert",
                related_donation_id=donation.id,
            )
            alerted_ngo_ids.append(cand["ngo_id"])

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
        create_notification(
            db=db,
            user_id=donation.donor_id,
            title=donor_title,
            message=donor_msg,
            type="emergency" if urgency == "CRITICAL" else "info",
            related_donation_id=donation.id,
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
            "ngo_count": len(selected_candidates),
            "alerted_ngo_ids": alerted_ngo_ids,
            "timeout_at": wave_timeout_at.isoformat(),
        })
        donation.alert_history_json = json.dumps(history_list)

        db.commit()
        db.refresh(donation)

        logger.info(
            f"[ProactiveDispatch] Donation #{donation.id} ({urgency}): Wave {current_wave} dispatched to "
            f"{len(selected_candidates)} NGOs (Timeout in {timeout_minutes}m)."
        )

        return {
            "status": "DISPATCHED",
            "donation_id": donation.id,
            "urgency": urgency,
            "wave": current_wave,
            "alerted_ngo_count": len(selected_candidates),
            "alerted_ngos": selected_candidates,
            "timeout_minutes": timeout_minutes,
        }

    @classmethod
    def check_and_escalate_unresponsive_waves(
        cls,
        db: Session,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scans pending donations with active alert waves.
        If a wave has timed out without NGO acceptance, automatically triggers Wave 2 or Admin Escalation.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        pending_donations = db.query(FoodDonation).filter(
            FoodDonation.status == "pending",
            FoodDonation.current_alert_wave > 0,
            FoodDonation.wave_timeout_at.isnot(None),
        ).all()

        escalated_results = []

        for donation in pending_donations:
            timeout_at = donation.wave_timeout_at
            if timeout_at and timeout_at.tzinfo is None:
                timeout_at = timeout_at.replace(tzinfo=timezone.utc)

            if timeout_at and now >= timeout_at:
                logger.info(f"[ProactiveDispatch] Donation #{donation.id} Wave {donation.current_alert_wave} timed out. Escalating.")
                # Mark timed-out offers as expired
                db.query(MatchOffer).filter(
                    MatchOffer.donation_id == donation.id,
                    MatchOffer.status == "offered",
                    MatchOffer.wave_number == donation.current_alert_wave
                ).update({"status": "expired"})
                db.commit()

                # Trigger next wave or critical escalation
                dispatch_res = cls.dispatch_proactive_alerts(
                    db, donation, reference_time=now, force_dispatch=True
                )
                escalated_results.append({
                    "donation_id": donation.id,
                    "previous_wave": donation.current_alert_wave - 1,
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
    ) -> Dict[str, Any]:
        """
        Atomic acceptance lock for NGOs.
        Guarantees that only ONE NGO can accept. Subsequent attempts receive 409 Conflict.
        Revokes all other outstanding wave invitations.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Fetch NGO entity
        ngo = db.query(NGO).filter(NGO.user_id == ngo_user_id).first()
        if not ngo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NGO profile not found for current user."
            )

        # 2. Acquire atomic database lock on the donation
        donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).with_for_update().first()
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found."
            )

        # 3. Check if already accepted or cancelled
        if donation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This donation has already been accepted by another organization or is no longer available."
            )

        # 4. Check if rescue window ended
        cls.evaluate_donation_urgency(db, donation, reference_time=now)
        if donation.remaining_minutes is not None and donation.remaining_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estimated rescue window has ended for this donation. Acceptance disabled."
            )

        # 5. Check NGO capacity
        if ngo.current_capacity is not None and ngo.current_capacity < donation.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient capacity ({ngo.current_capacity} meals available, {donation.quantity} required)."
            )

        # 6. Apply Atomic State Transition
        donation.status = "accepted"
        donation.assigned_ngo_id = ngo.id
        if ngo.current_capacity is not None:
            ngo.current_capacity = max(0.0, ngo.current_capacity - donation.quantity)

        # 7. Update winning offer and record response time
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

        # 9. Log donation history
        history = DonationHistory(
            donation_id=donation.id,
            old_status="pending",
            new_status="accepted",
            changed_by=ngo_user_id,
            remarks=f"Accepted by NGO: {ngo.organization_name} (Intake capacity reserved)."
        )
        db.add(history)

        # 10. Notify Donor
        donor = db.query(User).filter(User.id == donation.donor_id).first()
        create_notification(
            db=db,
            user_id=donation.donor_id,
            title="Food Donation Accepted by NGO",
            message=f"'{donation.food_name}' has been accepted by '{ngo.organization_name}'. Transport matching is in progress.",
            type="donation",
            related_donation_id=donation.id,
        )

        db.commit()
        db.refresh(donation)

        logger.info(
            f"[ProactiveDispatch] Donation #{donation.id} ATOMICALLY ACCEPTED by NGO #{ngo.id} ({ngo.organization_name})."
        )

        return {
            "status": "ACCEPTED",
            "donation_id": donation.id,
            "assigned_ngo_id": ngo.id,
            "organization_name": ngo.organization_name,
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

            return {
                "status": "SUCCESS",
                "timestamp": now.isoformat(),
                "active_donations_evaluated": evaluated_count,
                "dispatches_triggered": dispatched_count,
                "escalations_count": len(escalations),
            }
        finally:
            db.close()
