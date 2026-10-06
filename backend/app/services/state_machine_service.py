"""
State Machine Service: Centralized, Authoritative State Transition Engine for Smart Food Rescue.

Enforces valid state lifecycle transitions for:
1. FoodDonation (pending -> accepted -> volunteer_assigned / ngo_pickup -> collected -> delivered -> partially_distributed -> completed)
2. VolunteerAssignment (assigned -> accepted -> en_route -> arrived -> collected -> in_transit -> delivered / reassigned / cancelled / failed)
3. MatchOffer (offered -> accepted / rejected / expired / cancelled)

Prevents invalid or out-of-order state transitions, protects against race conditions,
and records immutable audit records in DonationHistory and AuditLog.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Set, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, object_session

from app.models.models import FoodDonation, VolunteerAssignment, DonationHistory, AuditLog, User
from app.services.security_service import log_rescue_operation

logger = logging.getLogger("smart_food_rescue.state_machine")

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ── Canonical Donation Status Constants ──────────────────────────────────────
class DonationStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    VOLUNTEER_ASSIGNED = "volunteer_assigned"
    PICKUP_EN_ROUTE = "pickup_en_route"
    ARRIVED_AT_DONOR = "arrived_at_donor"
    COLLECTED = "collected"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    PARTIALLY_DISTRIBUTED = "partially_distributed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PICKUP_FAILED = "pickup_failed"
    DELIVERY_FAILED = "delivery_failed"

# ── Canonical Assignment Status Constants ────────────────────────────────────
class AssignmentStatus:
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    COLLECTED = "collected"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REASSIGNED = "reassigned"
    FAILED = "failed"

# ── Legal Transition Graph for FoodDonation ──────────────────────────────────
# Maps current_status -> set of allowable next statuses
ALLOWED_DONATION_TRANSITIONS: Dict[str, Set[str]] = {
    DonationStatus.PENDING: {
        DonationStatus.PENDING,  # Idempotent
        DonationStatus.ACCEPTED,
        DonationStatus.VOLUNTEER_ASSIGNED,  # Direct courier dispatch
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
        DonationStatus.PICKUP_FAILED,       # Early failure report
    },
    DonationStatus.ACCEPTED: {
        DonationStatus.ACCEPTED,  # Idempotent
        DonationStatus.VOLUNTEER_ASSIGNED,
        DonationStatus.PICKUP_EN_ROUTE,
        DonationStatus.ARRIVED_AT_DONOR,
        DonationStatus.COLLECTED,  # Direct NGO self-pickup
        DonationStatus.PENDING,    # If NGO unassigns / passes
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.VOLUNTEER_ASSIGNED: {
        DonationStatus.VOLUNTEER_ASSIGNED,  # Idempotent
        DonationStatus.PICKUP_EN_ROUTE,
        DonationStatus.ARRIVED_AT_DONOR,
        DonationStatus.COLLECTED,
        DonationStatus.ACCEPTED,            # Volunteer unassigns / dynamic rematch back to accepted
        DonationStatus.CANCELLED,
        DonationStatus.PICKUP_FAILED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.PICKUP_EN_ROUTE: {
        DonationStatus.PICKUP_EN_ROUTE,  # Idempotent
        DonationStatus.ARRIVED_AT_DONOR,
        DonationStatus.COLLECTED,
        DonationStatus.VOLUNTEER_ASSIGNED,
        DonationStatus.ACCEPTED,         # Delay rematch
        DonationStatus.CANCELLED,
        DonationStatus.PICKUP_FAILED,
    },
    "en_route": {
        "en_route",
        DonationStatus.ARRIVED_AT_DONOR,
        DonationStatus.COLLECTED,
        DonationStatus.VOLUNTEER_ASSIGNED,
        DonationStatus.ACCEPTED,
        DonationStatus.CANCELLED,
        DonationStatus.PICKUP_FAILED,
    },
    DonationStatus.ARRIVED_AT_DONOR: {
        DonationStatus.ARRIVED_AT_DONOR,  # Idempotent
        DonationStatus.COLLECTED,
        DonationStatus.VOLUNTEER_ASSIGNED,  # Replacement courier dispatch if courier abandons before OTP
        DonationStatus.ACCEPTED,          # Rematch fallback
        DonationStatus.CANCELLED,
        DonationStatus.PICKUP_FAILED,
    },
    "arrived": {
        "arrived",
        DonationStatus.COLLECTED,
        DonationStatus.VOLUNTEER_ASSIGNED,
        DonationStatus.ACCEPTED,
        DonationStatus.CANCELLED,
        DonationStatus.PICKUP_FAILED,
    },
    DonationStatus.COLLECTED: {
        DonationStatus.COLLECTED,  # Idempotent
        DonationStatus.IN_TRANSIT,
        DonationStatus.DELIVERED,
        DonationStatus.DELIVERY_FAILED,
        DonationStatus.CANCELLED,
    },
    DonationStatus.IN_TRANSIT: {
        DonationStatus.IN_TRANSIT,  # Idempotent
        DonationStatus.DELIVERED,
        DonationStatus.COLLECTED,
        DonationStatus.DELIVERY_FAILED,
        DonationStatus.CANCELLED,
    },
    DonationStatus.DELIVERED: {
        DonationStatus.DELIVERED,  # Idempotent
        DonationStatus.PARTIALLY_DISTRIBUTED,
        DonationStatus.COMPLETED,
    },
    DonationStatus.PARTIALLY_DISTRIBUTED: {
        DonationStatus.PARTIALLY_DISTRIBUTED,  # Idempotent
        DonationStatus.COMPLETED,
    },
    DonationStatus.COMPLETED: {
        DonationStatus.COMPLETED,  # Terminal idempotent
    },
    DonationStatus.CANCELLED: {
        DonationStatus.CANCELLED,  # Terminal idempotent
    },
    DonationStatus.EXPIRED: {
        DonationStatus.EXPIRED,  # Terminal idempotent
    },
    DonationStatus.PICKUP_FAILED: {
        DonationStatus.PICKUP_FAILED,  # Idempotent
        DonationStatus.VOLUNTEER_ASSIGNED, # Dynamic rematch directly assigns replacement courier
        DonationStatus.ACCEPTED,       # Rematch fallback
        DonationStatus.PENDING,
        DonationStatus.CANCELLED,
    },
    DonationStatus.DELIVERY_FAILED: {
        DonationStatus.DELIVERY_FAILED,  # Idempotent
        DonationStatus.COMPLETED,        # Admin resolution
        DonationStatus.CANCELLED,
    },
}

# ── Role Permissions per Transition Edge ─────────────────────────────────────
ROLE_PERMITTED_TRANSITIONS: Dict[str, Dict[str, Set[str]]] = {
    DonationStatus.PENDING: {
        DonationStatus.ACCEPTED: {"ngo", "admin"},
        DonationStatus.VOLUNTEER_ASSIGNED: {"donor", "ngo", "volunteer", "admin"},
        DonationStatus.CANCELLED: {"donor", "admin"},
        DonationStatus.EXPIRED: {"admin", "system"},
        DonationStatus.PICKUP_FAILED: {"volunteer", "admin"},
    },
    DonationStatus.ACCEPTED: {
        DonationStatus.VOLUNTEER_ASSIGNED: {"donor", "ngo", "volunteer", "admin"},
        DonationStatus.PICKUP_EN_ROUTE: {"volunteer", "admin"},
        DonationStatus.ARRIVED_AT_DONOR: {"volunteer", "admin"},
        DonationStatus.COLLECTED: {"volunteer", "admin", "ngo"}, # Direct NGO pickup
        DonationStatus.PENDING: {"ngo", "admin"},                 # NGO unassign / pass
        DonationStatus.CANCELLED: {"donor", "ngo", "admin"},
        DonationStatus.EXPIRED: {"admin", "system"},
    },
    DonationStatus.VOLUNTEER_ASSIGNED: {
        DonationStatus.PICKUP_EN_ROUTE: {"volunteer", "admin"},
        DonationStatus.ARRIVED_AT_DONOR: {"volunteer", "admin"},
        DonationStatus.COLLECTED: {"volunteer", "admin", "ngo"},
        DonationStatus.DELIVERED: {"volunteer", "ngo", "admin"},
        DonationStatus.COMPLETED: {"volunteer", "ngo", "admin"},
        DonationStatus.ACCEPTED: {"volunteer", "admin", "ngo"},   # Dynamic rematch back to accepted
        DonationStatus.PICKUP_FAILED: {"volunteer", "admin"},
        DonationStatus.CANCELLED: {"donor", "admin"},
        DonationStatus.EXPIRED: {"admin", "system"},
    },
    DonationStatus.PICKUP_EN_ROUTE: {
        DonationStatus.ARRIVED_AT_DONOR: {"volunteer", "admin"},
        DonationStatus.COLLECTED: {"volunteer", "admin", "ngo"},
        DonationStatus.ACCEPTED: {"volunteer", "admin"},
        DonationStatus.PICKUP_FAILED: {"volunteer", "admin"},
        DonationStatus.CANCELLED: {"donor", "admin"},
    },
    DonationStatus.ARRIVED_AT_DONOR: {
        DonationStatus.COLLECTED: {"volunteer", "admin", "ngo"},
        DonationStatus.VOLUNTEER_ASSIGNED: {"system", "admin", "volunteer"},
        DonationStatus.ACCEPTED: {"volunteer", "admin"},
        DonationStatus.PICKUP_FAILED: {"volunteer", "admin"},
        DonationStatus.CANCELLED: {"donor", "admin"},
    },
    DonationStatus.COLLECTED: {
        DonationStatus.IN_TRANSIT: {"volunteer", "admin"},
        DonationStatus.DELIVERED: {"volunteer", "admin", "ngo"},
        DonationStatus.COMPLETED: {"volunteer", "ngo", "admin"},
        DonationStatus.DELIVERY_FAILED: {"volunteer", "admin"},
        DonationStatus.CANCELLED: {"donor", "admin"},
    },
    DonationStatus.IN_TRANSIT: {
        DonationStatus.DELIVERED: {"volunteer", "admin", "ngo"},
        DonationStatus.COMPLETED: {"volunteer", "ngo", "admin"},
        DonationStatus.DELIVERY_FAILED: {"volunteer", "admin"},
        DonationStatus.CANCELLED: {"donor", "admin"},
    },
    DonationStatus.DELIVERED: {
        DonationStatus.PARTIALLY_DISTRIBUTED: {"ngo", "admin"},
        DonationStatus.COMPLETED: {"ngo", "volunteer", "admin"},
    },
    DonationStatus.PARTIALLY_DISTRIBUTED: {
        DonationStatus.PARTIALLY_DISTRIBUTED: {"ngo", "admin"},
        DonationStatus.COMPLETED: {"ngo", "admin"},
    },
    DonationStatus.PICKUP_FAILED: {
        DonationStatus.PENDING: {"admin", "donor"},
        DonationStatus.ACCEPTED: {"admin", "donor"},
        DonationStatus.CANCELLED: {"admin", "donor"},
    },
    DonationStatus.DELIVERY_FAILED: {
        DonationStatus.COMPLETED: {"admin", "ngo"},
        DonationStatus.CANCELLED: {"admin"},
    },
}

ALLOWED_ASSIGNMENT_TRANSITIONS: Dict[str, Set[str]] = {
    AssignmentStatus.ASSIGNED: {
        AssignmentStatus.ASSIGNED,
        AssignmentStatus.ACCEPTED,
        AssignmentStatus.EN_ROUTE,
        AssignmentStatus.ARRIVED,
        AssignmentStatus.COLLECTED,
        AssignmentStatus.CANCELLED,
        AssignmentStatus.REASSIGNED,
        AssignmentStatus.FAILED,
    },
    AssignmentStatus.ACCEPTED: {
        AssignmentStatus.ACCEPTED,
        AssignmentStatus.EN_ROUTE,
        AssignmentStatus.ARRIVED,
        AssignmentStatus.COLLECTED,
        AssignmentStatus.CANCELLED,
        AssignmentStatus.REASSIGNED,
        AssignmentStatus.FAILED,
    },
    AssignmentStatus.EN_ROUTE: {
        AssignmentStatus.EN_ROUTE,
        AssignmentStatus.ARRIVED,
        AssignmentStatus.COLLECTED,
        AssignmentStatus.CANCELLED,
        AssignmentStatus.REASSIGNED,
        AssignmentStatus.FAILED,
    },
    AssignmentStatus.ARRIVED: {
        AssignmentStatus.ARRIVED,
        AssignmentStatus.COLLECTED,
        AssignmentStatus.CANCELLED,
        AssignmentStatus.REASSIGNED,
        AssignmentStatus.FAILED,
    },
    AssignmentStatus.COLLECTED: {
        AssignmentStatus.COLLECTED,
        AssignmentStatus.IN_TRANSIT,
        AssignmentStatus.DELIVERED,
        AssignmentStatus.CANCELLED,
        AssignmentStatus.FAILED,
    },
    AssignmentStatus.IN_TRANSIT: {
        AssignmentStatus.IN_TRANSIT,
        AssignmentStatus.DELIVERED,
        AssignmentStatus.FAILED,
        AssignmentStatus.CANCELLED,
    },
    AssignmentStatus.DELIVERED: {
        AssignmentStatus.DELIVERED,
    },
    AssignmentStatus.CANCELLED: {
        AssignmentStatus.CANCELLED,
    },
    AssignmentStatus.REASSIGNED: {
        AssignmentStatus.REASSIGNED,
    },
    AssignmentStatus.FAILED: {
        AssignmentStatus.FAILED,
    },
}


# ── Authoritative State Transition Functions ─────────────────────────────────

def validate_donation_transition(
    old_status: str,
    new_status: str,
    caller_role: Optional[str] = None,
    force: bool = False,
) -> bool:
    """
    Validates if transitioning from old_status to new_status is permitted.
    Admin overrides are allowed when explicitly requested with force=True.
    """
    if force:
        return True

    allowed = ALLOWED_DONATION_TRANSITIONS.get(old_status)
    if allowed is None:
        logger.warning(f"Unknown current donation status '{old_status}' encountered.")
        return False

    if new_status not in allowed:
        return False

    if caller_role and caller_role.lower() not in ["admin", "system"]:
        role_map = ROLE_PERMITTED_TRANSITIONS.get(old_status, {})
        allowed_roles = role_map.get(new_status)
        if allowed_roles is not None and caller_role.lower() not in allowed_roles:
            return False

    return True


def transition_donation_state(
    donation: FoodDonation,
    new_status: str,
    actor: Optional[User] = None,
    reason: str = "",
    db: Optional[Session] = None,
    force: bool = False,
    changed_by_user_id: Optional[int] = None,
    caller_role: Optional[str] = None,
) -> FoodDonation:
    """
    Canonical, centralized state-transition mechanism for Smart Food Rescue.

    Enforces:
    1. Validation of current state against allowed transition graph.
    2. Rejection of illegal state jumps (raises HTTP 409 Conflict).
    3. Verification of caller role authorization (raises HTTP 403 Forbidden).
    4. Safe handling of idempotent self-transitions.
    5. Atomic update of donation.status and updated_at.
    6. Automatic creation and flushing of DonationHistory.
    7. Recording of AuditLog for security traceability.
    """
    session = db or object_session(donation)
    if session is None:
        raise ValueError("A database Session is required to execute state transition.")

    old_status = donation.status.lower() if donation.status else DonationStatus.PENDING
    target_status = new_status.lower()

    # Determine actor identity (actor can be a User object, string name, or None)
    user_id = changed_by_user_id or (getattr(actor, "id", None) if actor else None)
    role = caller_role or (getattr(actor, "role", None) if actor else None)
    role_clean = role.lower() if role else None

    # Handle idempotent self-transition
    if old_status == target_status:
        logger.debug(f"[State Machine] Idempotent transition for Donation #{donation.id}: '{old_status}'")
        return donation

    # Determine valid target transitions for current status
    allowed_targets = ALLOWED_DONATION_TRANSITIONS.get(old_status) or []

    # Force flag bypasses graph and role restrictions
    if not force:
        # 1. State machine graph check (applies to ALL callers including admin unless force=True)
        if target_status not in allowed_targets:
            error_msg = f"Illegal donation state transition from '{old_status}' to '{target_status}'."
            logger.error(f"[State Machine] Violation: Donation #{donation.id} - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )

        # 2. Role permission check (if caller role is specified and not admin/system)
        if role_clean and role_clean not in ["admin", "system"]:
            permitted_roles = ROLE_PERMITTED_TRANSITIONS.get(old_status, {}).get(target_status)
            if permitted_roles is not None and role_clean not in permitted_roles:
                perm_err = f"Role '{role_clean}' is not authorized to transition donation from '{old_status}' to '{target_status}'."
                logger.error(f"[State Machine] Auth Violation: Donation #{donation.id} - {perm_err}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=perm_err,
                )

    # Apply atomic state update
    donation.status = target_status
    donation.updated_at = _utcnow()

    # Create immutable DonationHistory record
    history = DonationHistory(
        donation_id=donation.id,
        old_status=old_status,
        new_status=target_status,
        changed_by=user_id,
        remarks=reason or f"Transitioned from {old_status} to {target_status}"
    )
    session.add(history)

    # Record security audit log
    audit_entry = AuditLog(
        user_id=user_id,
        action=f"donation_state_transition_{target_status}",
        resource_type="donation",
        resource_id=donation.id,
        status="success",
        details=f"State changed from '{old_status}' to '{target_status}'. Reason: {reason or 'None'}. Role: {role_clean or 'unspecified'}"
    )
    session.add(audit_entry)
    session.flush()

    logger.info(
        f"[State Machine] Donation #{donation.id}: '{old_status}' -> '{target_status}' "
        f"(by user={user_id}, role={role_clean}, reason='{reason}')"
    )

    return donation


def transition_donation_status(
    db: Session,
    donation: FoodDonation,
    new_status: Optional[str] = None,
    changed_by_user_id: Optional[int] = None,
    remarks: str = "",
    caller_role: Optional[str] = None,
    force: bool = False,
    actor: Optional[User] = None,
    target_status: Optional[str] = None,
) -> FoodDonation:
    """
    Backward-compatible adapter for existing calls to transition_donation_status.
    Delegates directly to transition_donation_state.
    Accepts either `new_status` or `target_status`.
    """
    resolved_status = new_status or target_status
    if not resolved_status:
        raise ValueError("Either new_status or target_status must be provided.")
    return transition_donation_state(
        donation=donation,
        new_status=resolved_status,
        actor=actor,
        reason=remarks,
        db=db,
        force=force,
        changed_by_user_id=changed_by_user_id,
        caller_role=caller_role,
    )


def transition_assignment_status(
    db: Session,
    assignment: VolunteerAssignment,
    new_status: str,
    changed_by_user_id: Optional[int] = None,
    remarks: str = "",
    caller_role: Optional[str] = None,
    force: bool = False,
) -> VolunteerAssignment:
    """
    Authoritative state transition engine for VolunteerAssignment records.
    - Validates legal courier assignment transition
    - Automatically updates relevant lifecycle timestamps (accepted_at, collected_at, delivered_at)
    - Raises HTTP 409 Conflict on illegal transition
    """
    old_status = assignment.status.lower() if assignment.status else AssignmentStatus.ASSIGNED
    target_status = new_status.lower()

    if old_status == target_status:
        return assignment

    if not (force or caller_role == "admin"):
        allowed = ALLOWED_ASSIGNMENT_TRANSITIONS.get(old_status, set())
        if target_status not in allowed:
            error_msg = f"Illegal assignment state transition from '{old_status}' to '{target_status}'."
            logger.error(f"[State Machine] Violation: Assignment ID {assignment.id} - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )

    now = _utcnow()
    assignment.status = target_status

    if target_status == AssignmentStatus.ACCEPTED and not assignment.accepted_at:
        assignment.accepted_at = now
    elif target_status == AssignmentStatus.COLLECTED and not assignment.collected_at:
        assignment.collected_at = now
    elif target_status == AssignmentStatus.DELIVERED and not assignment.delivered_at:
        assignment.delivered_at = now

    db.flush()

    logger.info(
        f"[State Machine] Assignment #{assignment.id}: '{old_status}' -> '{target_status}' "
        f"(by user={changed_by_user_id})"
    )

    return assignment
