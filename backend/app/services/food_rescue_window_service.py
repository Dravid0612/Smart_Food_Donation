"""
Time-Aware Food Rescue Window & Feasibility Engine
===================================================
Calculates advisory food rescue windows, urgency levels, and logistical feasibility
without ever making microbiological food-safety claims.

Strict Food Safety Rule:
"Visual assessment only. This does not certify food safety."
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app.services.food_knowledge_rules import resolve_food_profile, FoodProfile

FOOD_SAFETY_DISCLAIMER = "Image analysis cannot guarantee food safety. Visual assessment only. This is an advisory estimate and does not certify food safety."

# ── Canonical Rescue Urgency Constants & Thresholds ──────────────────────────
class RescueUrgencyLevel:
    FRESH = "FRESH"
    APPROACHING = "APPROACHING"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"
    RESCUE_WINDOW_ENDED = "RESCUE_WINDOW_ENDED"

# Authoritative Urgency Thresholds (in remaining minutes)
THRESHOLD_FRESH_MINUTES = 180        # > 180m (> 3h): FRESH
THRESHOLD_APPROACHING_MINUTES = 120  # 121m - 180m (2 - 3h): APPROACHING
THRESHOLD_URGENT_MINUTES = 45        # 46m - 120m (45m - 2h): URGENT
THRESHOLD_CRITICAL_MINUTES = 0       # 1m - 45m: CRITICAL; <= 0: RESCUE_WINDOW_ENDED

def map_remaining_minutes_to_urgency(remaining_minutes: int) -> Tuple[str, float]:
    """
    Authoritative Urgency Level & Score mapping for Smart Food Rescue.
    Returns: (urgency_level, urgency_score)
    - <= 0: RESCUE_WINDOW_ENDED (1.0)
    - 1 to 45: CRITICAL (0.95)
    - 46 to 120: URGENT (0.75)
    - 121 to 180: APPROACHING (0.45)
    - > 180: FRESH (0.15)
    """
    if remaining_minutes <= THRESHOLD_CRITICAL_MINUTES:
        return RescueUrgencyLevel.RESCUE_WINDOW_ENDED, 1.0
    elif remaining_minutes <= THRESHOLD_URGENT_MINUTES:
        return RescueUrgencyLevel.CRITICAL, 0.95
    elif remaining_minutes <= THRESHOLD_APPROACHING_MINUTES:
        return RescueUrgencyLevel.URGENT, 0.75
    elif remaining_minutes <= THRESHOLD_FRESH_MINUTES:
        return RescueUrgencyLevel.APPROACHING, 0.45
    else:
        return RescueUrgencyLevel.FRESH, 0.15

def calculate_elapsed_prep_time(
    prepared_at: datetime,
    current_time: Optional[datetime] = None
) -> Tuple[float, str]:
    """
    Calculates elapsed hours and human-readable string since food preparation.
    Rejects or handles future timestamps cleanly.
    """
    now = current_time or datetime.now(timezone.utc)
    if prepared_at.tzinfo is None:
        prepared_at = prepared_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    diff_seconds = (now - prepared_at).total_seconds()
    if diff_seconds < 0:
        # Invalid future preparation time
        return 0.0, "Prepared just now (0m)"

    elapsed_hours = diff_seconds / 3600.0
    hours = int(elapsed_hours)
    minutes = int((diff_seconds % 3600) / 60)

    if hours > 0:
        elapsed_str = f"{hours}h {minutes}m"
    else:
        elapsed_str = f"{minutes}m"

    return elapsed_hours, elapsed_str

def calculate_storage_effective_life(
    profile: FoodProfile,
    storage_method: str,
    storage_continuous: bool,
    storage_history: Optional[List[Dict[str, Any]]],
    elapsed_prep_hours: float
) -> Tuple[float, List[str]]:
    """
    Calculates the total advisory window hours based on storage mode and transitions.
    """
    reasons = []
    
    # Base shelf hours by mode
    method_clean = storage_method.strip() if storage_method else "Room Temperature"
    if method_clean == "Refrigerated":
        base_window = profile.base_shelf_hours_refrigerated
        reasons.append(f"Storage: Refrigerated (Advisory base {base_window:.0f}h)")
    elif method_clean in ["Hot Holding", "Heated/Insulated", "Insulated Container"]:
        base_window = profile.base_shelf_hours_hot_holding or profile.base_shelf_hours_room_temp
        reasons.append(f"Storage: {method_clean} (Advisory base {base_window:.0f}h)")
    elif method_clean == "Frozen":
        base_window = 72.0
        reasons.append(f"Storage: Frozen (Advisory base {base_window:.0f}h)")
    else:
        base_window = profile.base_shelf_hours_room_temp
        reasons.append(f"Storage: Ambient Room Temperature (Advisory base {base_window:.0f}h)")

    # History penalty if storage conditions changed (e.g. Hot holding -> Ambient)
    history_penalty_hours = 0.0
    if not storage_continuous and storage_history:
        reasons.append(f"Storage history indicates {len(storage_history)} condition transitions")
        for stage in storage_history:
            mode = stage.get("method", "Room Temperature")
            dur = float(stage.get("duration_hours", 0.5))
            if mode == "Room Temperature" and method_clean != "Room Temperature":
                history_penalty_hours += (dur * 1.5)
    elif not storage_continuous:
        history_penalty_hours = 0.5
        reasons.append("Storage condition non-continuous; applied conservative margin")

    effective_total_hours = max(1.0, base_window - history_penalty_hours)
    return effective_total_hours, reasons

def evaluate_food_rescue_window(
    food_type: Optional[str],
    food_category: str,
    prepared_at: datetime,
    storage_method: str = "Room Temperature",
    storage_continuous: bool = True,
    storage_history: Optional[List[Dict[str, Any]]] = None,
    packaging_status: str = "Covered",
    previously_served: str = "No",
    exposure_status: str = "No",
    handling_status: str = "No",
    visual_condition_in: Optional[str] = None,
    visible_spoilage_in: Optional[str] = None,
    ai_confidence_in: Optional[float] = None,
    is_custom: bool = False,
    current_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Core Time-Aware Food Rescue Window Service.
    Produces the THREE distinct outputs:
    1. VISUAL CONDITION (GOOD / FAIR / CONCERNING / UNCERTAIN)
    2. ESTIMATED REMAINING-USE WINDOW (start, end, remaining_minutes)
    3. RESCUE URGENCY (FRESH / APPROACHING / URGENT / CRITICAL)
    Along with rule_coverage ('HIGH', 'MEDIUM', 'LOW').
    """
    now = current_time or datetime.now(timezone.utc)
    if prepared_at.tzinfo is None:
        prepared_at = prepared_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Resolve auditable food profile & calculate rule coverage
    from app.services.food_knowledge_rules import calculate_rule_coverage
    profile = resolve_food_profile(food_type, food_category)
    rule_coverage = calculate_rule_coverage(food_type, food_category, is_custom=is_custom)

    # 2. Elapsed preparation duration
    elapsed_hours, elapsed_str = calculate_elapsed_prep_time(prepared_at, now)

    # 3. Storage effective duration
    total_window_hours, storage_reasons = calculate_storage_effective_life(
        profile, storage_method, storage_continuous, storage_history, elapsed_hours
    )

    reasons = [
        f"Food item classified as {profile.food_type} ({profile.category})",
        f"Food was prepared {elapsed_str} ago ({prepared_at.strftime('%d %b %I:%M %p')})",
    ] + storage_reasons

    if is_custom:
        if rule_coverage == "LOW":
            reasons.append("Limited food-specific information is available; conservative advisory estimate applied.")
        else:
            reasons.append(f"Custom food evaluated under {profile.category} generic category parameters.")

    # 4. Packaging and exposure deductions
    handling_deduction_hours = 0.0
    if packaging_status == "Open" or exposure_status == "Yes":
        handling_deduction_hours += 1.0
        reasons.append("Packaging open or exposed to ambient environment")
    elif packaging_status == "Partially Covered":
        handling_deduction_hours += 0.5
        reasons.append("Packaging partially covered")
    else:
        reasons.append(f"Packaging: {packaging_status}")

    if previously_served == "Yes":
        handling_deduction_hours += 1.0
        reasons.append("Food was previously presented for serving")
    if handling_status == "Yes":
        handling_deduction_hours += 1.0
        reasons.append("Food had direct guest/customer handling")

    adjusted_total_hours = max(0.5, total_window_hours - handling_deduction_hours)

    # Handle future preparation timestamp gracefully
    if prepared_at > now:
        effective_prep = now
        reasons.append(f"Preparation timestamp is in the future ({prepared_at.strftime('%d %b %I:%M %p')}); baseline calculated from current time.")
    else:
        effective_prep = prepared_at

    window_end = effective_prep + timedelta(hours=adjusted_total_hours)

    # Remaining duration
    remaining_seconds = (window_end - now).total_seconds()
    if remaining_seconds <= 0:
        remaining_minutes = 0
    else:
        remaining_minutes = int(remaining_seconds / 60)

    # 5. Output 1: Visual Condition
    # Handle AI vision inputs or set deterministic defaults
    if visible_spoilage_in and "Visible" in visible_spoilage_in:
        visual_condition = "CONCERNING"
        reasons.append("Visible surface irregularities detected by visual check")
    elif visual_condition_in in ["GOOD", "FAIR", "CONCERNING", "UNCERTAIN"]:
        visual_condition = visual_condition_in
        if visual_condition == "UNCERTAIN":
            reasons.append("Visual condition uncertain due to lighting or camera angle")
        else:
            reasons.append(f"Visual condition assessed as {visual_condition}")
    else:
        visual_condition = "GOOD"
        reasons.append("No obvious visible spoilage detected")

    # 6. Output 2: Estimated Remaining-Use / Rescue Window
    window_hours_left = remaining_minutes / 60.0
    if remaining_minutes <= 0:
        window_display = "Rescue Window Ended"
    elif window_hours_left < 1.0:
        window_display = f"~{remaining_minutes} minutes"
    elif window_hours_left <= 2.0:
        window_display = f"~1–2 hours ({remaining_minutes} min remaining)"
    else:
        window_display = f"~{window_hours_left:.1f} hours ({remaining_minutes} min remaining)"

    # 7. Output 3: Authoritative Rescue Urgency Level & Score
    urgency_level, urgency_score = map_remaining_minutes_to_urgency(remaining_minutes)

    # AI confidence rating
    confidence = ai_confidence_in or 0.88
    if confidence < 0.65:
        visual_condition = "UNCERTAIN"

    return {
        "assessment_status": "ADVISORY",
        "food_type": profile.food_type,
        "food_category": profile.category,
        "rule_source": profile.source,
        "rule_version": profile.rule_version,
        "rule_coverage": rule_coverage,
        "is_custom": is_custom,
        "visual_condition": visual_condition,
        "estimated_window_start": prepared_at.isoformat(),
        "estimated_window_end": window_end.isoformat(),
        "remaining_minutes": remaining_minutes,
        "estimated_window_display": window_display,
        "urgency_level": urgency_level,
        "urgency_score": urgency_score,
        "confidence": confidence,
        "reasons": reasons,
        "safety_disclaimer": FOOD_SAFETY_DISCLAIMER,
        "disclaimer": FOOD_SAFETY_DISCLAIMER
    }

def calculate_rescue_feasibility(
    remaining_window_minutes: int,
    estimated_pickup_minutes: float = 15.0,
    estimated_travel_minutes: float = 20.0,
    ngo_intake_minutes: float = 10.0,
    safety_buffer_minutes: float = 15.0
) -> Dict[str, Any]:
    """
    Logistics Feasibility Engine:
    Checks: T_pickup + T_travel + T_intake + T_buffer < remaining_rescue_window
    Outputs: RESCUE_FEASIBLE / AT_RISK / RESCUE_UNLIKELY
    """
    total_required_minutes = (
        estimated_pickup_minutes +
        estimated_travel_minutes +
        ngo_intake_minutes +
        safety_buffer_minutes
    )

    remaining_buffer = remaining_window_minutes - (estimated_pickup_minutes + estimated_travel_minutes + ngo_intake_minutes)

    if remaining_window_minutes <= 0:
        return {
            "feasibility_status": "RESCUE_UNLIKELY",
            "feasibility_label": "Rescue Window Ended",
            "is_feasible": False,
            "estimated_pickup_minutes": estimated_pickup_minutes,
            "estimated_travel_minutes": estimated_travel_minutes,
            "ngo_intake_minutes": ngo_intake_minutes,
            "safety_buffer_minutes": safety_buffer_minutes,
            "total_required_minutes": total_required_minutes,
            "remaining_buffer_minutes": 0,
            "explanation": "Advisory rescue deadline reached. Food rescue window has ended."
        }

    if remaining_window_minutes >= total_required_minutes:
        feasibility_status = "RESCUE_FEASIBLE"
        feasibility_label = "Rescue Feasible"
        is_feasible = True
        explanation = f"Estimated trip duration ({int(total_required_minutes - safety_buffer_minutes)}m) leaves a healthy buffer of {int(remaining_buffer)}m."
    elif remaining_window_minutes >= (total_required_minutes - safety_buffer_minutes):
        feasibility_status = "AT_RISK"
        feasibility_label = "Rescue at Risk"
        is_feasible = True
        explanation = f"Tight timeline ({int(remaining_window_minutes)}m window remaining). Courier and NGO must expedite handover without delay."
    else:
        feasibility_status = "RESCUE_UNLIKELY"
        feasibility_label = "Rescue Unlikely"
        is_feasible = False
        explanation = f"Estimated rescue time ({int(total_required_minutes)}m) exceeds remaining advisory rescue window ({remaining_window_minutes}m)."

    return {
        "feasibility_status": feasibility_status,
        "feasibility_label": feasibility_label,
        "is_feasible": is_feasible,
        "estimated_pickup_minutes": estimated_pickup_minutes,
        "estimated_travel_minutes": estimated_travel_minutes,
        "ngo_intake_minutes": ngo_intake_minutes,
        "safety_buffer_minutes": safety_buffer_minutes,
        "total_required_minutes": total_required_minutes,
        "remaining_buffer_minutes": max(0, int(remaining_buffer)),
        "explanation": explanation
    }
