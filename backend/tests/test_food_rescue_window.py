import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment
from app.services.food_rescue_window_service import (
    evaluate_food_rescue_window,
    calculate_rescue_feasibility,
    map_remaining_minutes_to_urgency,
    RescueUrgencyLevel,
    THRESHOLD_FRESH_MINUTES,
    THRESHOLD_APPROACHING_MINUTES,
    THRESHOLD_URGENT_MINUTES,
    THRESHOLD_CRITICAL_MINUTES,
)
from app.services.urgency_service import (
    calculate_authoritative_urgency,
    calculate_urgency,
    calculate_urgency_score,
)
from app.services.proactive_dispatch_service import ProactiveDispatchService
from app.core.security import create_access_token

client = TestClient(app)


def _auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def erw_test_users(db_session: Session):
    """Provides verified donor, ngo, and volunteer users for ERW testing."""
    donor = db_session.query(User).filter(User.email == "erw_donor@test.com").first()
    if not donor:
        donor = User(
            name="ERW Donor",
            email="erw_donor@test.com",
            password_hash="testpasshash",
            phone="9876543210",
            role="donor",
            is_active=True,
            latitude=12.9716,
            longitude=77.5946,
        )
        db_session.add(donor)
        db_session.commit()
        db_session.refresh(donor)

    ngo_user = db_session.query(User).filter(User.email == "erw_ngo@test.com").first()
    if not ngo_user:
        ngo_user = User(
            name="ERW NGO Rep",
            email="erw_ngo@test.com",
            password_hash="testpasshash",
            phone="9876543211",
            role="ngo",
            is_active=True,
            latitude=12.9750,
            longitude=77.5980,
        )
        db_session.add(ngo_user)
        db_session.commit()
        db_session.refresh(ngo_user)

    ngo_profile = db_session.query(NGO).filter(NGO.user_id == ngo_user.id).first()
    if not ngo_profile:
        ngo_profile = NGO(
            user_id=ngo_user.id,
            organization_name="ERW Hope Shelter",
            contact_phone="9876543211",
            address="100 Shelter Road",
            is_verified=True,
            is_available=True,
            capacity=500,
            current_capacity=500,
            latitude=12.9750,
            longitude=77.5980,
        )
        db_session.add(ngo_profile)
        db_session.commit()
        db_session.refresh(ngo_profile)

    volunteer = db_session.query(User).filter(User.email == "erw_vol@test.com").first()
    if not volunteer:
        volunteer = User(
            name="ERW Courier",
            email="erw_vol@test.com",
            password_hash="testpasshash",
            phone="9876543212",
            role="volunteer",
            is_active=True,
            vehicle_type="bike",
            carrying_capacity=50,
            latitude=12.9720,
            longitude=77.5950,
        )
        db_session.add(volunteer)
        db_session.commit()
        db_session.refresh(volunteer)

    return {"donor": donor, "ngo_user": ngo_user, "ngo": ngo_profile, "volunteer": volunteer}


# ── TEST 1: Fresh Food (> 180 min remaining) ──────────────────────────────────
def test_erw_fresh_food():
    """Fresh food (> 180m remaining) evaluates to FRESH urgency with feasible logistics."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Cooked food base is 4.0h (240m) at ambient, prepared 20 mins ago -> 220 min remaining
    prepared_at = now - timedelta(minutes=20)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=prepared_at,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Covered",
        previously_served="No",
        exposure_status="No",
        handling_status="No",
        current_time=now,
    )

    assert result["remaining_minutes"] > THRESHOLD_FRESH_MINUTES
    assert result["urgency_level"] == RescueUrgencyLevel.FRESH
    assert result["urgency_score"] == 0.15
    assert "remaining" in result["estimated_window_display"]

    feasibility = calculate_rescue_feasibility(result["remaining_minutes"])
    assert feasibility["feasibility_status"] == "RESCUE_FEASIBLE"
    assert feasibility["is_feasible"] is True


# ── TEST 2: Approaching Food (121 - 180 min remaining) ────────────────────────
def test_erw_approaching_food():
    """Approaching food (121m - 180m remaining) evaluates to APPROACHING urgency."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Base 4.0h (240m). Prepared 90m ago -> 150 min remaining (between 121 and 180)
    prepared_at = now - timedelta(minutes=90)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=prepared_at,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Covered",
        previously_served="No",
        exposure_status="No",
        handling_status="No",
        current_time=now,
    )

    assert THRESHOLD_APPROACHING_MINUTES < result["remaining_minutes"] <= THRESHOLD_FRESH_MINUTES
    assert result["urgency_level"] == RescueUrgencyLevel.APPROACHING
    assert result["urgency_score"] == 0.45


# ── TEST 3: Urgent Food (46 - 120 min remaining) ──────────────────────────────
def test_erw_urgent_food():
    """Urgent food (46m - 120m remaining) evaluates to URGENT urgency."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Base 4.0h (240m). Deduct 1h for Open packaging -> 3.0h total.
    # Prepared 110m ago -> 70m remaining (between 46 and 120)
    prepared_at = now - timedelta(minutes=110)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=prepared_at,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Open",
        previously_served="No",
        exposure_status="No",
        handling_status="No",
        current_time=now,
    )

    assert THRESHOLD_URGENT_MINUTES < result["remaining_minutes"] <= THRESHOLD_APPROACHING_MINUTES
    assert result["urgency_level"] == RescueUrgencyLevel.URGENT
    assert result["urgency_score"] == 0.75


# ── TEST 4: Critical Food (1 - 45 min remaining) ──────────────────────────────
def test_erw_critical_food():
    """Critical food (1m - 45m remaining) evaluates to CRITICAL urgency."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Base 4.0h (240m). Prepared 210m (3.5h) ago -> 30 min remaining (between 1 and 45)
    prepared_at = now - timedelta(minutes=210)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=prepared_at,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Covered",
        previously_served="No",
        exposure_status="No",
        handling_status="No",
        current_time=now,
    )

    assert THRESHOLD_CRITICAL_MINUTES < result["remaining_minutes"] <= THRESHOLD_URGENT_MINUTES
    assert result["urgency_level"] == RescueUrgencyLevel.CRITICAL
    assert result["urgency_score"] == 0.95


# ── TEST 5: Expired Food (<= 0 min remaining) ─────────────────────────────────
def test_erw_expired_food():
    """Expired food (remaining <= 0m) evaluates to RESCUE_WINDOW_ENDED and is_feasible False."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Prepared 5 hours ago for a 4.0h base food item -> already expired 60 minutes ago
    prepared_at = now - timedelta(hours=5)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=prepared_at,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Covered",
        current_time=now,
    )

    assert result["remaining_minutes"] == 0
    assert result["urgency_level"] == RescueUrgencyLevel.RESCUE_WINDOW_ENDED
    assert result["urgency_score"] == 1.0
    assert result["estimated_window_display"] == "Rescue Window Ended"

    feasibility = calculate_rescue_feasibility(result["remaining_minutes"])
    assert feasibility["feasibility_status"] == "RESCUE_UNLIKELY"
    assert feasibility["is_feasible"] is False
    assert feasibility["feasibility_label"] == "Rescue Window Ended"


# ── TEST 6: Future Preparation Timestamp ──────────────────────────────────────
def test_erw_future_preparation_timestamp():
    """Future preparation timestamps are handled gracefully without negative elapsed times or crashes."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Accidental future timestamp entered by user (1 hour in the future)
    future_prep = now + timedelta(hours=1)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=future_prep,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Covered",
        current_time=now,
    )

    # Effective preparation baseline is capped at current time
    assert result["remaining_minutes"] > 0
    assert result["urgency_level"] in [RescueUrgencyLevel.FRESH, RescueUrgencyLevel.APPROACHING]
    # Reasons list explicitly documents the future timestamp handling
    reasons_str = " ".join(result["reasons"])
    assert "future" in reasons_str.lower() or "just now" in reasons_str.lower()


# ── TEST 7: Boundary Exactly at Expiry ─────────────────────────────────────────
def test_erw_boundary_exactly_at_expiry():
    """Boundary test: exactly at expiry moment (delta = 0) evaluates to RESCUE_WINDOW_ENDED."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Rice base is 4.0 hours. Exactly 4.0 hours ago = 0 seconds remaining.
    prepared_at = now - timedelta(hours=4)

    result = evaluate_food_rescue_window(
        food_type="Rice",
        food_category="Cooked Food",
        prepared_at=prepared_at,
        storage_method="Room Temperature",
        storage_continuous=True,
        packaging_status="Covered",
        current_time=now,
    )

    assert result["remaining_minutes"] == 0
    assert result["urgency_level"] == RescueUrgencyLevel.RESCUE_WINDOW_ENDED
    assert result["estimated_window_display"] == "Rescue Window Ended"

    feasibility = calculate_rescue_feasibility(result["remaining_minutes"])
    assert feasibility["is_feasible"] is False
    assert feasibility["feasibility_status"] == "RESCUE_UNLIKELY"


# ── TEST 8: Authoritative Deadline Synchronization ────────────────────────────
def test_erw_authoritative_deadline_synchronization(db_session: Session, erw_test_users):
    """ProactiveDispatchService synchronizes estimated_window_end and expiry_time consistently."""
    donor = erw_test_users["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Sync Deadline Test Biryani",
        food_category="Cooked Food",
        quantity=30,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="Sync Test Counter",
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Run authoritative evaluation
    eval_res = ProactiveDispatchService.evaluate_donation_urgency(db_session, donation, reference_time=now)

    assert eval_res["urgency_level"] in [RescueUrgencyLevel.FRESH, RescueUrgencyLevel.APPROACHING, RescueUrgencyLevel.URGENT]
    # Verify strict synchronization between estimated_window_end and expiry_time
    assert donation.estimated_window_end is not None
    assert donation.expiry_time is not None
    assert abs((donation.estimated_window_end - donation.expiry_time).total_seconds()) < 1.0
    assert donation.rescue_urgency_level == eval_res["urgency_level"]


# ── TEST 9: Execution-Time ERW Re-evaluation Rejects Stale Acceptance ───────────
def test_erw_execution_time_recheck_accept_donation_blocked_when_window_ended(db_session: Session, erw_test_users):
    """Donation whose rescue window has ended cannot be accepted by an NGO, even if created when fresh."""
    donor = erw_test_users["donor"]
    ngo_user = erw_test_users["ngo_user"]
    now = datetime.now(timezone.utc)

    # Donation created when fresh, but elapsed time pushed it past deadline
    past_expiry = now - timedelta(minutes=10)
    past_prep = now - timedelta(hours=6)

    stale_donation = FoodDonation(
        donor_id=donor.id,
        food_name="Stale Curried Rice",
        food_category="Cooked Food",
        quantity=20,
        quantity_unit="Meals",
        preparation_time=past_prep,
        expiry_time=past_expiry,
        estimated_window_end=past_expiry,
        remaining_minutes=0,
        rescue_urgency_level="RESCUE_WINDOW_ENDED",
        pickup_address="Stale Kitchen",
        status="pending",  # Status was pending, but window has ended
    )
    db_session.add(stale_donation)
    db_session.commit()
    db_session.refresh(stale_donation)

    # NGO attempts to accept stale donation
    headers = _auth_header(ngo_user)
    resp = client.post(f"/api/donations/{stale_donation.id}/accept", headers=headers)

    # Must be rejected with 400 Bad Request or 409 Conflict
    assert resp.status_code in [400, 409]
    assert "rescue window has ended" in resp.json()["detail"].lower()


# ── TEST 10: Execution-Time ERW Re-evaluation Rejects Expired Volunteer Dispatch ─
def test_erw_execution_time_recheck_volunteer_dispatch_blocked_when_window_ended(db_session: Session, erw_test_users):
    """Cannot assign volunteer to a donation whose rescue window has ended."""
    donor = erw_test_users["donor"]
    ngo_user = erw_test_users["ngo_user"]
    volunteer = erw_test_users["volunteer"]
    now = datetime.now(timezone.utc)

    past_expiry = now - timedelta(minutes=5)
    past_prep = now - timedelta(hours=5)

    expired_accepted_donation = FoodDonation(
        donor_id=donor.id,
        food_name="Expired Accepted Food",
        food_category="Cooked Food",
        quantity=15,
        quantity_unit="Meals",
        preparation_time=past_prep,
        expiry_time=past_expiry,
        estimated_window_end=past_expiry,
        remaining_minutes=0,
        rescue_urgency_level="RESCUE_WINDOW_ENDED",
        pickup_address="Closed Kitchen",
        status="accepted",
        assigned_ngo_id=erw_test_users["ngo"].id,
    )
    db_session.add(expired_accepted_donation)
    db_session.commit()
    db_session.refresh(expired_accepted_donation)

    # Attempting to assign volunteer
    headers = _auth_header(ngo_user)
    assign_resp = client.post(
        f"/api/volunteers/assignments?donation_id={expired_accepted_donation.id}&volunteer_id={volunteer.id}",
        headers=headers,
    )
    assert assign_resp.status_code == 400
    assert "rescue window has ended" in assign_resp.json()["detail"].lower()


# ── TEST 11: Urgency Service Canonical Mapping ────────────────────────────────
def test_erw_urgency_service_canonical_mapping():
    """calculate_authoritative_urgency and calculate_urgency correctly reflect canonical states."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Fresh (> 180 min)
    exp_fresh = now + timedelta(minutes=240)
    level, score = calculate_authoritative_urgency(now, exp_fresh, current_time=now)
    assert level == RescueUrgencyLevel.FRESH
    assert score == 0.15
    assert calculate_urgency(now, exp_fresh, current_time=now) == "Fresh"

    # 2. Approaching (121 - 180 min)
    exp_approaching = now + timedelta(minutes=150)
    level, score = calculate_authoritative_urgency(now, exp_approaching, current_time=now)
    assert level == RescueUrgencyLevel.APPROACHING
    assert score == 0.45
    assert calculate_urgency(now, exp_approaching, current_time=now) == "Use Soon"

    # 3. Urgent (46 - 120 min)
    exp_urgent = now + timedelta(minutes=80)
    level, score = calculate_authoritative_urgency(now, exp_urgent, current_time=now)
    assert level == RescueUrgencyLevel.URGENT
    assert score == 0.75
    assert calculate_urgency(now, exp_urgent, current_time=now) == "Urgent"

    # 4. Critical (1 - 45 min)
    exp_critical = now + timedelta(minutes=30)
    level, score = calculate_authoritative_urgency(now, exp_critical, current_time=now)
    assert level == RescueUrgencyLevel.CRITICAL
    assert score == 0.95
    assert calculate_urgency(now, exp_critical, current_time=now) == "Urgent"

    # 5. Expired (<= 0 min)
    exp_ended = now - timedelta(minutes=5)
    level, score = calculate_authoritative_urgency(now, exp_ended, current_time=now)
    assert level == RescueUrgencyLevel.RESCUE_WINDOW_ENDED
    assert score == 1.0
    assert calculate_urgency(now, exp_ended, current_time=now) == "Expired"
