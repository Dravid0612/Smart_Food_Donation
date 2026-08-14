import math
from datetime import datetime, timezone

CATEGORY_DECAY_RATES = {
    "Cooked Food": 3.5,
    "Bakery": 1.8,
    "Fruits": 1.5,
    "Vegetables": 1.5,
    "Packaged Food": 0.5,
    "Other": 1.0
}

def calculate_urgency(prep_time: datetime, expiry_time: datetime) -> str:
    """
    Calculates time-based urgency level for food donation:
    - Fresh: More than 60% remaining time.
    - Use Soon: 30-60% remaining time.
    - Urgent: Less than 30% remaining time.
    - Expired: Expiry time passed.
    """
    now = datetime.now(timezone.utc)
    if prep_time.tzinfo is None:
        prep_time = prep_time.replace(tzinfo=timezone.utc)
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if now >= expiry_time:
        return "Expired"

    total_duration = (expiry_time - prep_time).total_seconds()
    if total_duration <= 0:
        return "Expired"

    remaining_duration = (expiry_time - now).total_seconds()
    ratio = remaining_duration / total_duration

    if ratio > 0.60:
        return "Fresh"
    elif ratio >= 0.30:
        return "Use Soon"
    elif ratio > 0:
        return "Urgent"
    else:
        return "Expired"

def calculate_urgency_score(prep_time: datetime, expiry_time: datetime, food_category: str = "Cooked Food") -> float:
    """
    Calculates continuous continuous exponential urgency score U(t) in range [0.0, 1.0].
    Higher score indicates higher urgency to deliver food immediately.
    """
    now = datetime.now(timezone.utc)
    if prep_time.tzinfo is None:
        prep_time = prep_time.replace(tzinfo=timezone.utc)
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if now >= expiry_time:
        return 0.0

    total_seconds = max(1.0, (expiry_time - prep_time).total_seconds())
    remaining_seconds = max(0.0, (expiry_time - now).total_seconds())

    alpha = CATEGORY_DECAY_RATES.get(food_category, 1.0)
    time_elapsed_ratio = 1.0 - (remaining_seconds / total_seconds)

    # Exponential urgency growth as expiry approaches
    score = math.exp(alpha * time_elapsed_ratio) / math.exp(alpha)
    return max(0.0, min(1.0, score))

