import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.models.models import FoodDonation, VolunteerAssignment, DonationHistory, AuditLog, User, NGO
from app.services.state_machine_service import (
    DonationStatus,
    AssignmentStatus,
    transition_donation_state,
    transition_donation_status,
    transition_assignment_status,
    validate_donation_transition,
    ALLOWED_DONATION_TRANSITIONS,
)


def _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Vegetable Pulao",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=4),
        pickup_address="Indiranagar 100ft Rd, Bangalore",
        status=initial_status,
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)
    return donation


# ── 1. Matrix & Graph Validation ─────────────────────────────────────────────

def test_validate_donation_transition_matrix():
    # Valid forward moves
    assert validate_donation_transition(DonationStatus.PENDING, DonationStatus.ACCEPTED) is True
    assert validate_donation_transition(DonationStatus.ACCEPTED, DonationStatus.VOLUNTEER_ASSIGNED) is True
    assert validate_donation_transition(DonationStatus.ACCEPTED, DonationStatus.COLLECTED) is True  # NGO self-pickup
    assert validate_donation_transition(DonationStatus.VOLUNTEER_ASSIGNED, DonationStatus.COLLECTED) is True
    assert validate_donation_transition(DonationStatus.COLLECTED, DonationStatus.DELIVERED) is True
    assert validate_donation_transition(DonationStatus.DELIVERED, DonationStatus.COMPLETED) is True

    # Idempotent moves
    assert validate_donation_transition(DonationStatus.PENDING, DonationStatus.PENDING) is True
    assert validate_donation_transition(DonationStatus.COLLECTED, DonationStatus.COLLECTED) is True

    # Illegal backward / skip moves
    assert validate_donation_transition(DonationStatus.COMPLETED, DonationStatus.PENDING) is False
    assert validate_donation_transition(DonationStatus.PENDING, DonationStatus.DELIVERED) is False
    assert validate_donation_transition(DonationStatus.DELIVERED, DonationStatus.ACCEPTED) is False
    assert validate_donation_transition(DonationStatus.CANCELLED, DonationStatus.COLLECTED) is False

    # Admin override
    assert validate_donation_transition(DonationStatus.COMPLETED, DonationStatus.PENDING, force=True) is True
    assert validate_donation_transition(DonationStatus.CANCELLED, DonationStatus.ACCEPTED, force=True) is True


# ── 2. Valid Full Golden Path ────────────────────────────────────────────────

def test_valid_full_lifecycle_transitions(db_session):
    """Verifies complete deterministic path: pending -> accepted -> volunteer_assigned -> en_route -> arrived -> collected -> in_transit -> delivered -> partially_distributed -> completed"""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    assert donor_user is not None
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING)

    # 1. Pending -> Accepted
    transition_donation_state(donation, DonationStatus.ACCEPTED, actor="Shelter NGO", reason="NGO accepted rescue", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.ACCEPTED

    # 2. Accepted -> Volunteer Assigned
    transition_donation_state(donation, DonationStatus.VOLUNTEER_ASSIGNED, actor="Dispatcher", reason="Volunteer assigned", db=db_session, caller_role="admin")
    assert donation.status == DonationStatus.VOLUNTEER_ASSIGNED

    # 3. Volunteer Assigned -> Pickup En Route
    transition_donation_state(donation, DonationStatus.PICKUP_EN_ROUTE, actor="Volunteer Ramesh", reason="Traveling to donor location", db=db_session, caller_role="volunteer")
    assert donation.status == DonationStatus.PICKUP_EN_ROUTE

    # 4. Pickup En Route -> Arrived at Donor
    transition_donation_state(donation, DonationStatus.ARRIVED_AT_DONOR, actor="Volunteer Ramesh", reason="Arrived at donor location", db=db_session, caller_role="volunteer")
    assert donation.status == DonationStatus.ARRIVED_AT_DONOR

    # 5. Arrived -> Handover / Collected
    transition_donation_state(donation, DonationStatus.COLLECTED, actor="Volunteer Ramesh", reason="Handover completed with OTP", db=db_session, caller_role="volunteer")
    assert donation.status == DonationStatus.COLLECTED

    # 6. Collected -> In Transit
    transition_donation_state(donation, DonationStatus.IN_TRANSIT, actor="Volunteer Ramesh", reason="In transit to NGO shelter", db=db_session, caller_role="volunteer")
    assert donation.status == DonationStatus.IN_TRANSIT

    # 7. In Transit -> Delivered
    transition_donation_state(donation, DonationStatus.DELIVERED, actor="Volunteer Ramesh", reason="Delivered at receiving NGO", db=db_session, caller_role="volunteer")
    assert donation.status == DonationStatus.DELIVERED

    # 8. Delivered -> Partially Distributed
    transition_donation_state(donation, DonationStatus.PARTIALLY_DISTRIBUTED, actor="Shelter Staff", reason="Distributed 30 meals", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.PARTIALLY_DISTRIBUTED

    # 9. Partially Distributed -> Completed
    transition_donation_state(donation, DonationStatus.COMPLETED, actor="Shelter Staff", reason="Final 20 meals distributed", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.COMPLETED

    # Check history records count matches transitions
    histories = db_session.query(DonationHistory).filter(DonationHistory.donation_id == donation.id).all()
    assert len(histories) == 9


# ── 3. Invalid Transition Rejected ───────────────────────────────────────────

def test_invalid_transition_rejected_with_409(db_session):
    """Direct jump from pending to delivered without acceptance or pickup must be rejected with 409 Conflict."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING)

    with pytest.raises(HTTPException) as exc_info:
        transition_donation_state(
            donation,
            DonationStatus.DELIVERED,
            actor="Bad Actor",
            reason="Illegal jump",
            db=db_session,
            caller_role="volunteer"
        )
    assert exc_info.value.status_code == 409
    assert "Illegal donation state transition" in exc_info.value.detail


# ── 4. Duplicate / Idempotent Transition ─────────────────────────────────────

def test_duplicate_transition_idempotent(db_session):
    """Re-submitting the exact same status should succeed idempotently without error."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.ACCEPTED)

    # Calling transition to already accepted status
    result = transition_donation_state(
        donation,
        DonationStatus.ACCEPTED,
        actor="Shelter NGO",
        reason="Duplicate network retry",
        db=db_session,
        caller_role="ngo"
    )
    assert result.status == DonationStatus.ACCEPTED


# ── 5. Cancelled Donation (Terminal State) ───────────────────────────────────

def test_cancelled_donation_lifecycle(db_session):
    """Donation cancelled by donor cannot transition to active states like accepted or collected."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING)

    # Cancel donation
    transition_donation_state(donation, DonationStatus.CANCELLED, actor=donor_user.name, reason="Food no longer available", db=db_session, caller_role="donor")
    assert donation.status == DonationStatus.CANCELLED

    # Illegal attempt to resurrect cancelled donation to accepted
    with pytest.raises(HTTPException) as exc_info:
        transition_donation_state(donation, DonationStatus.ACCEPTED, actor="NGO", reason="Trying to accept", db=db_session, caller_role="ngo")
    assert exc_info.value.status_code == 409


# ── 6. Expired Rescue Window (Terminal State) ────────────────────────────────

def test_expired_rescue_window_lifecycle(db_session):
    """Expired donation cannot be accepted or collected."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING)

    # Expire donation
    transition_donation_state(donation, DonationStatus.EXPIRED, actor="System", reason="Advisory rescue window elapsed", db=db_session, caller_role="system")
    assert donation.status == DonationStatus.EXPIRED

    # Attempt to collect expired food
    with pytest.raises(HTTPException) as exc_info:
        transition_donation_state(donation, DonationStatus.COLLECTED, actor="Volunteer", reason="Picking up anyway", db=db_session, caller_role="volunteer")
    assert exc_info.value.status_code == 409


# ── 7. NGO Acceptance & Role Checking ────────────────────────────────────────

def test_ngo_acceptance_role_enforcement(db_session):
    """Only NGO or Admin can accept a pending donation. Volunteers or Donors are rejected with 403 Forbidden."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING)

    # Volunteer attempting to accept pending donation -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        transition_donation_state(donation, DonationStatus.ACCEPTED, actor="Volunteer", reason="Self acceptance", db=db_session, caller_role="volunteer")
    assert exc_info.value.status_code == 403

    # NGO accepting -> Success
    transition_donation_state(donation, DonationStatus.ACCEPTED, actor="Care Shelter NGO", reason="Approved intake", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.ACCEPTED


# ── 8. Volunteer Assignment ──────────────────────────────────────────────────

def test_volunteer_assignment_transition(db_session):
    """Accepted donation moves to volunteer_assigned."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.ACCEPTED)

    transition_donation_state(donation, DonationStatus.VOLUNTEER_ASSIGNED, actor="Coordinator", reason="Courier assigned", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.VOLUNTEER_ASSIGNED


# ── 9. Handover / Direct NGO Self-Pickup ─────────────────────────────────────

def test_ngo_self_pickup_handover(db_session):
    """NGO can directly self-pickup (accepted -> collected) without intermediate volunteer."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.ACCEPTED)

    transition_donation_state(donation, DonationStatus.COLLECTED, actor="NGO Driver", reason="Direct NGO pickup at donor venue", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.COLLECTED


# ── 10. Distribution & Completion ────────────────────────────────────────────

def test_distribution_and_completion_lifecycle(db_session):
    """Delivered donation can be partially distributed, then marked completed."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.DELIVERED)

    # 1. Partial distribution
    transition_donation_state(donation, DonationStatus.PARTIALLY_DISTRIBUTED, actor="NGO Staff", reason="Distributed to block A", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.PARTIALLY_DISTRIBUTED

    # 2. Final distribution completion
    transition_donation_state(donation, DonationStatus.COMPLETED, actor="NGO Staff", reason="Distributed to block B - 100% finished", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.COMPLETED

    # 3. Completed is terminal idempotent
    transition_donation_state(donation, DonationStatus.COMPLETED, actor="NGO Staff", reason="Idempotent check", db=db_session, caller_role="ngo")
    assert donation.status == DonationStatus.COMPLETED


# ── 11. Admin Intervention ───────────────────────────────────────────────────

def test_admin_intervention_override(db_session):
    """Admin can intervene and execute force transitions with mandatory reason recorded."""
    admin_user = db_session.query(User).filter(User.role == "admin").first()
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    assert admin_user is not None
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PICKUP_FAILED)

    # Admin intervenes to reset donation to accepted for rematching
    transition_donation_state(
        donation,
        DonationStatus.ACCEPTED,
        actor=admin_user.name,
        reason="Admin Intervention: Resetting to accepted for fallback dispatcher",
        db=db_session,
        caller_role="admin",
        force=True
    )
    assert donation.status == DonationStatus.ACCEPTED

    # Verify audit log and donation history
    history = db_session.query(DonationHistory).filter(
        DonationHistory.donation_id == donation.id,
        DonationHistory.new_status == DonationStatus.ACCEPTED
    ).first()
    assert history is not None
    assert "Admin Intervention" in history.remarks


# ── 12. Every State Change Creates DonationHistory & AuditLog ────────────────

def test_every_state_change_creates_donation_history_and_audit(db_session):
    """Strict check that every state mutation persists a new DonationHistory record and AuditLog."""
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.PENDING)

    initial_hist_count = db_session.query(DonationHistory).filter(DonationHistory.donation_id == donation.id).count()
    initial_audit_count = db_session.query(AuditLog).filter(AuditLog.resource_id == donation.id).count()

    # Step 1: Pending -> Accepted
    transition_donation_state(donation, DonationStatus.ACCEPTED, actor="NGO Officer", reason="Accepting food offer", db=db_session, caller_role="ngo")
    # Step 2: Accepted -> Volunteer Assigned
    transition_donation_state(donation, DonationStatus.VOLUNTEER_ASSIGNED, actor="Admin Officer", reason="Assigning volunteer", db=db_session, caller_role="admin")
    # Step 3: Volunteer Assigned -> Collected
    transition_donation_state(donation, DonationStatus.COLLECTED, actor="Volunteer Officer", reason="Pickup verified", db=db_session, caller_role="volunteer")

    final_hist_count = db_session.query(DonationHistory).filter(DonationHistory.donation_id == donation.id).count()
    final_audit_count = db_session.query(AuditLog).filter(AuditLog.resource_id == donation.id).count()

    assert final_hist_count == initial_hist_count + 3
    assert final_audit_count == initial_audit_count + 3


# ── 13. Volunteer Assignment Status Lifecycle ────────────────────────────────

def test_transition_assignment_status_lifecycle(db_session):
    donor_user = db_session.query(User).filter(User.role == "donor").first()
    volunteer_user = db_session.query(User).filter(User.role == "volunteer").first()
    assert donor_user is not None
    assert volunteer_user is not None

    donation = _make_sample_donation(db_session, donor_user, initial_status=DonationStatus.ACCEPTED)

    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer_user.id,
        status=AssignmentStatus.ASSIGNED,
    )
    db_session.add(assignment)
    db_session.commit()
    db_session.refresh(assignment)

    # 1. Accept assignment
    transition_assignment_status(db_session, assignment, AssignmentStatus.ACCEPTED, changed_by_user_id=volunteer_user.id)
    assert assignment.status == AssignmentStatus.ACCEPTED
    assert assignment.accepted_at is not None

    # 2. Arrived at donor
    transition_assignment_status(db_session, assignment, AssignmentStatus.ARRIVED, changed_by_user_id=volunteer_user.id)
    assert assignment.status == AssignmentStatus.ARRIVED

    # 3. Collected
    transition_assignment_status(db_session, assignment, AssignmentStatus.COLLECTED, changed_by_user_id=volunteer_user.id)
    assert assignment.status == AssignmentStatus.COLLECTED
    assert assignment.collected_at is not None

    # 4. Delivered
    transition_assignment_status(db_session, assignment, AssignmentStatus.DELIVERED, changed_by_user_id=volunteer_user.id)
    assert assignment.status == AssignmentStatus.DELIVERED
    assert assignment.delivered_at is not None
