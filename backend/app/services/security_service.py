import time
from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import AuditLog, User, NGO, FoodDonation, VolunteerAssignment
from app.core.config import settings

# In-memory sliding-window failed attempts cache: {identifier: [timestamps]}
_FAILED_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
MAX_FAILED_ATTEMPTS = settings.MAX_FAILED_LOGIN_ATTEMPTS
LOCKOUT_WINDOW_SECONDS = settings.LOGIN_LOCKOUT_WINDOW_SECONDS


def check_login_rate_limit(identifier: str):
    """
    Brute-force protection: Blocks login attempts if more than MAX_FAILED_ATTEMPTS
    occur within the LOCKOUT_WINDOW_SECONDS window.
    """
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(identifier, [])
    # Filter attempts within the window
    recent_attempts = [ts for ts in attempts if now - ts < LOCKOUT_WINDOW_SECONDS]
    _FAILED_LOGIN_ATTEMPTS[identifier] = recent_attempts

    if len(recent_attempts) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 5 minutes."
        )

def record_login_failure(identifier: str):
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(identifier, [])
    attempts.append(now)
    _FAILED_LOGIN_ATTEMPTS[identifier] = attempts

def reset_login_failures(identifier: str):
    if identifier in _FAILED_LOGIN_ATTEMPTS:
        _FAILED_LOGIN_ATTEMPTS.pop(identifier, None)

def log_audit_event(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    status_code: str = "success",
    details: Optional[str] = None
):
    """
    Records an immutable audit log entry for security and compliance tracking.
    Never stores passwords or raw authentication tokens.
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            status=status_code,
            details=details
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry
    except Exception as e:
        db.rollback()
        # Fallback print without interrupting primary workflow
        print(f"[SECURITY AUDIT LOG ERROR]: {e}")
        return None

# Server-Side Valid State Transition Matrix
# Mapping: current_status -> {target_status: [authorized_roles]}
VALID_DONATION_TRANSITIONS = {
    "pending": {
        "accepted": ["ngo", "admin"],
        "cancelled": ["donor", "admin"],
        "expired": ["admin"]
    },
    "accepted": {
        "volunteer_assigned": ["donor", "ngo", "volunteer", "admin"],
        "pickup_en_route": ["volunteer", "admin"],
        "arrived_at_donor": ["volunteer", "admin"],
        "collected": ["volunteer", "admin", "ngo"], # direct pickup
        "delivered": ["ngo", "volunteer", "admin"],
        "completed": ["ngo", "volunteer", "admin"],
        "cancelled": ["donor", "ngo", "admin"]
    },
    "volunteer_assigned": {
        "pickup_en_route": ["volunteer", "admin"],
        "arrived_at_donor": ["volunteer", "admin"],
        "collected": ["volunteer", "admin", "ngo"],
        "delivered": ["volunteer", "ngo", "admin"],
        "completed": ["volunteer", "ngo", "admin"],
        "pickup_failed": ["volunteer", "admin"],
        "cancelled": ["donor", "admin"]
    },
    "pickup_en_route": {
        "arrived_at_donor": ["volunteer", "admin"],
        "collected": ["volunteer", "admin", "ngo"],
        "pickup_failed": ["volunteer", "admin"],
        "cancelled": ["donor", "admin"]
    },
    "arrived_at_donor": {
        "collected": ["volunteer", "admin", "ngo"],
        "pickup_failed": ["volunteer", "admin"],
        "cancelled": ["donor", "admin"]
    },
    "collected": {
        "in_transit": ["volunteer", "admin"],
        "delivered": ["volunteer", "admin"],
        "completed": ["volunteer", "ngo", "admin"],
        "delivery_failed": ["volunteer", "admin"]
    },
    "in_transit": {
        "delivered": ["volunteer", "admin"],
        "completed": ["volunteer", "ngo", "admin"],
        "delivery_failed": ["volunteer", "admin"]
    },
    "delivered": {
        "completed": ["ngo", "volunteer", "admin"],
        "partially_distributed": ["ngo", "admin"],
        "distribution_pending": ["ngo", "admin"]
    },
    "distribution_pending": {
        "partially_distributed": ["ngo", "admin"],
        "completed": ["ngo", "admin"]
    },
    "partially_distributed": {
        "partially_distributed": ["ngo", "admin"],
        "completed": ["ngo", "admin"]
    },
    "completed": {}, # Terminal state
    "cancelled": {}, # Terminal state
    "pickup_failed": {
        "pending": ["admin", "donor"],
        "cancelled": ["admin", "donor"]
    },
    "delivery_failed": {
        "completed": ["admin", "ngo"]
    },
    "expired": {} # Terminal state
}

def validate_donation_transition(current_status: str, target_status: str, user_role: str):
    """
    Strict server-side finite state machine (FSM) validation for food donations.
    Rejects invalid jumps or unauthorized state transitions.
    """
    curr = current_status.lower()
    tgt = target_status.lower()
    role = user_role.lower()

    if curr == tgt:
        # Idempotent state transition
        return True

    allowed_targets = VALID_DONATION_TRANSITIONS.get(curr, {})
    if tgt not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid donation state transition from '{curr}' to '{tgt}'."
        )

    authorized_roles = allowed_targets[tgt]
    if role not in authorized_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to transition donation from '{curr}' to '{tgt}'."
        )

    return True
