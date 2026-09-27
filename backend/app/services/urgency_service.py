import math
from datetime import datetime, timezone
from typing import Optional, Tuple
from app.services.food_rescue_window_service import (
    map_remaining_minutes_to_urgency,
    RescueUrgencyLevel,
    THRESHOLD_CRITICAL_MINUTES,
    THRESHOLD_URGENT_MINUTES,
    THRESHOLD_APPROACHING_MINUTES,
    THRESHOLD_FRESH_MINUTES,
)

CATEGORY_DECAY_RATES = {
    "Cooked Food": 3.5,
    "Bakery": 1.8,
    "Fruits": 1.5,
    "Vegetables": 1.5,
    "Packaged Food": 0.5,
    "Other": 1.0
}

def calculate_authoritative_urgency(
    prep_time: Optional[datetime],
    expiry_time: Optional[datetime],
    current_time: Optional[datetime] = None
) -> Tuple[str, float]:
    """
    Authoritative backend calculation for food rescue urgency level and score.
    Returns: (RescueUrgencyLevel, urgency_score)
    Semantics: FRESH, APPROACHING, URGENT, CRITICAL, RESCUE_WINDOW_ENDED.
    """
    now = current_time or datetime.now(timezone.utc)
    if expiry_time and expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if not expiry_time or now >= expiry_time:
        return RescueUrgencyLevel.RESCUE_WINDOW_ENDED, 1.0

    diff_sec = (expiry_time - now).total_seconds()
    remaining_min = int(diff_sec / 60) if diff_sec > 0 else 0
    return map_remaining_minutes_to_urgency(remaining_min)

def calculate_urgency(prep_time: datetime, expiry_time: datetime, current_time: Optional[datetime] = None) -> str:
    """
    Calculates time-based urgency level for food donation aligned with canonical ERW thresholds:
    - Fresh: More than 180 min remaining (> 3h).
    - Use Soon: 121-180 min remaining (2-3h).
    - Urgent: <= 120 min remaining (<= 2h).
    - Expired: Expiry time reached or passed (<= 0m).
    """
    now = current_time or datetime.now(timezone.utc)
    if prep_time and prep_time.tzinfo is None:
        prep_time = prep_time.replace(tzinfo=timezone.utc)
    if expiry_time and expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if not expiry_time or now >= expiry_time:
        return "Expired"

    diff_seconds = (expiry_time - now).total_seconds()
    if diff_seconds <= 0:
        return "Expired"

    remaining_minutes = int(diff_seconds / 60)

    if remaining_minutes <= THRESHOLD_CRITICAL_MINUTES:
        return "Expired"
    elif remaining_minutes <= THRESHOLD_URGENT_MINUTES:
        return "Urgent"
    elif remaining_minutes <= THRESHOLD_APPROACHING_MINUTES:
        return "Urgent"
    elif remaining_minutes <= THRESHOLD_FRESH_MINUTES:
        return "Use Soon"
    else:
        return "Fresh"

def calculate_urgency_score(prep_time: datetime, expiry_time: datetime, food_category: str = "Cooked Food") -> float:
    """
    Continuous urgency score in range [0.0, 1.0].
    Synchronized with canonical ERW mapping while respecting exponential decay when relevant.
    """
    now = datetime.now(timezone.utc)
    if prep_time and prep_time.tzinfo is None:
        prep_time = prep_time.replace(tzinfo=timezone.utc)
    if expiry_time and expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if not expiry_time or now >= expiry_time:
        return 1.0

    diff_seconds = (expiry_time - now).total_seconds()
    if diff_seconds <= 0:
        return 1.0

    remaining_minutes = int(diff_seconds / 60)
    _, score = map_remaining_minutes_to_urgency(remaining_minutes)
    return score


