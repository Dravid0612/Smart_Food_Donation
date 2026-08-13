from datetime import datetime, timezone

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
