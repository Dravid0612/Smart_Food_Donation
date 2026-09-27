"""
Phase 5 Test Suite: Logistics Feasibility + Dynamic Rematching
===============================================================
Comprehensive verification of:
1. Exact Feasibility Model (T_pickup + buffer_pickup + T_transit + buffer_intake + buffer_traffic <= remaining_ERW)
2. Strict Feasibility Hard Gate (Reliability score CANNOT override rescue-window infeasibility)
3. Location Telemetry Freshness (Actual timestamp check; ETA value alone does not imply stale telemetry)
4. Stale Telemetry Rematch Trigger (GPS ping older than threshold automatically triggers dynamic rematch)
5. Courier Cancellation & Vehicle Breakdown Handling (Automated fallback & backup courier assignment)
6. Preservation of Historical Assignment Records (Zero deletions, old assignments marked reassigned)
7. Non-Blaming Trilingual Notifications (Objective, respectful, multilingual messaging)
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.models import (
    User, NGO, FoodDonation, VolunteerAssignment, DonationHistory, Notification
)
from app.services.food_rescue_window_service import calculate_rescue_feasibility
from app.services.rematching_service import (
    RematchingService,
    HANDOVER_BUFFER_MIN,
    NGO_INTAKE_BUFFER_MIN,
    CRITICAL_SAFETY_MARGIN_MIN,
    TELEMETRY_STALE_MINUTES,
)
from app.services.recommendation_service import recommend_volunteers
from app.core.security import hash_password, create_access_token


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def _create_user(db: Session, email: str, role: str, name: str, phone: str = "9876543210", **kwargs) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password("Secret123!"),
            role=role,
            name=name,
            phone=phone,
            is_active=True,
            **kwargs
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        for k, v in kwargs.items():
            setattr(user, k, v)
        db.commit()
        db.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role, "user_id": user.id, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TEST 1: Feasibility Model Exact Buffers and ERW Comparison
# ==============================================================================
def test_01_feasibility_model_exact_buffers_and_erw(db: Session):
    """
    FEASIBILITY MODEL:
    mission_time = courier -> donor ETA + pickup buffer (10) + donor -> NGO ETA + intake buffer (10) + traffic contingency (5)
    FEASIBLE iff mission_time <= remaining ERW; INFEASIBLE iff mission_time > remaining ERW.
    """
    now = datetime.now(timezone.utc)

    # 1. Test calculation engine constants
    assert HANDOVER_BUFFER_MIN == 10.0
    assert NGO_INTAKE_BUFFER_MIN == 10.0
    assert CRITICAL_SAFETY_MARGIN_MIN == 5.0
    total_buffers = HANDOVER_BUFFER_MIN + NGO_INTAKE_BUFFER_MIN + CRITICAL_SAFETY_MARGIN_MIN
    assert total_buffers == 25.0

    # 2. Test calculate_rescue_feasibility from food_rescue_window_service
    # Case A: 120 minutes window, 15m pickup, 20m travel, 10m intake, 15m buffer -> total 60m <= 120m -> FEASIBLE
    res_feasible = calculate_rescue_feasibility(
        remaining_window_minutes=120,
        estimated_pickup_minutes=15.0,
        estimated_travel_minutes=20.0,
        ngo_intake_minutes=10.0,
        safety_buffer_minutes=15.0
    )
    assert res_feasible["is_feasible"] is True
    assert res_feasible["feasibility_status"] == "RESCUE_FEASIBLE"
    assert res_feasible["total_required_minutes"] == 60.0

    # Case B: 30 minutes window, 15m pickup, 20m travel, 10m intake, 15m buffer -> total 60m > 30m -> INFEASIBLE
    res_infeasible = calculate_rescue_feasibility(
        remaining_window_minutes=30,
        estimated_pickup_minutes=15.0,
        estimated_travel_minutes=20.0,
        ngo_intake_minutes=10.0,
        safety_buffer_minutes=15.0
    )
    assert res_infeasible["is_feasible"] is False
    assert res_infeasible["feasibility_status"] == "RESCUE_UNLIKELY"

    # 3. Test RematchingService.evaluate_assignment_feasibility
    donor = _create_user(db, "donor_model@test.com", "donor", "Donor Feasibility")
    vol = _create_user(db, "vol_model@test.com", "volunteer", "Vol Feasibility", latitude=12.9716, longitude=77.5946)

    # Donation with 120 min remaining window
    donation_feasible = FoodDonation(
        donor_id=donor.id,
        food_name="Feasible Meals",
        food_category="Cooked Food",
        quantity=30.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(minutes=120),
        estimated_window_end=now + timedelta(minutes=120),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="accepted"
    )
    db.add(donation_feasible)
    db.commit()

    eval_feas = RematchingService.evaluate_assignment_feasibility(
        db=db,
        donation=donation_feasible,
        volunteer=vol,
        current_eta_minutes=10.0,
        reference_time=now
    )
    # total = 10 (pickup) + 10 (handover) + 15 (ngo transit) + 10 (intake) + 5 (traffic) = 50 min <= 120 min
    assert eval_feas["is_feasible"] is True
    assert eval_feas["total_required_minutes"] == 50.0

    # Donation with only 25 min remaining window (mission takes 50 min)
    donation_tight = FoodDonation(
        donor_id=donor.id,
        food_name="Tight Meals",
        food_category="Cooked Food",
        quantity=30.0,
        preparation_time=now - timedelta(hours=3),
        expiry_time=now + timedelta(minutes=25),
        estimated_window_end=now + timedelta(minutes=25),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="accepted"
    )
    db.add(donation_tight)
    db.commit()

    eval_tight = RematchingService.evaluate_assignment_feasibility(
        db=db,
        donation=donation_tight,
        volunteer=vol,
        current_eta_minutes=10.0,
        reference_time=now
    )
    assert eval_tight["is_feasible"] is False
    assert eval_tight["total_required_minutes"] == 50.0
    assert eval_tight["remaining_window_minutes"] == 25.0


# ==============================================================================
# TEST 2: Strict Reliability Gate - High Reliability CANNOT Override Infeasibility
# ==============================================================================
def test_02_strict_reliability_gate_rejects_infeasible_courier(db: Session, client: TestClient):
    """
    Important Rule:
    A courier having a high reliability score must NOT override rescue-window infeasibility.
    E.g.: Reliability = 99% BUT ETA exceeds rescue window -> Result: REJECT (score = 0.0).
    A feasible courier with lower reliability (e.g. 75%) MUST rank higher.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    donor = _create_user(db, f"donor_gate_{ts}@test.com", "donor", "Donor Gate", latitude=12.9716, longitude=77.5946)

    # Vol A: Excellent reliability (99.0%), but FAR AWAY (15 km -> pickup ETA ~45m -> total mission ~90m)
    vol_a_star = _create_user(
        db, f"vol_star_{ts}@test.com", "volunteer", "Star Courier (Far)",
        reliability_score=99.0,
        carrying_capacity=100,
        latitude=13.1000, # Far away
        longitude=77.7000
    )

    # Vol B: Moderate reliability (75.0%), but VERY CLOSE (0.5 km -> pickup ETA ~5m -> total mission ~50m)
    vol_b_local = _create_user(
        db, f"vol_local_{ts}@test.com", "volunteer", "Local Courier (Near)",
        reliability_score=75.0,
        carrying_capacity=100,
        latitude=12.9720, # Very close
        longitude=77.5950
    )

    # Donation has 60 minutes remaining in rescue window (prepared 3 hours ago out of 4h standard window)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name=f"Urgent Surplus {ts}",
        food_category="Cooked Food",
        quantity=40.0,
        preparation_time=now - timedelta(hours=3),
        expiry_time=now + timedelta(minutes=60),
        estimated_window_end=now + timedelta(minutes=60),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="accepted"
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    # Run recommendation service
    recs = recommend_volunteers(db, donation)
    recs_map = {r["volunteer_id"]: r for r in recs}

    assert vol_a_star.id in recs_map
    assert vol_b_local.id in recs_map

    rec_a = recs_map[vol_a_star.id]
    rec_b = recs_map[vol_b_local.id]

    # Star courier: total mission time exceeds 55m window -> MUST be rejected (score = 0.0)
    assert rec_a["is_feasible"] is False
    assert rec_a["score"] == 0.0
    assert "REJECTED" in rec_a["reason"]
    assert "cannot override rescue window infeasibility" in rec_a["reason"]

    # Local courier: feasible -> score > 0.0
    assert rec_b["is_feasible"] is True
    assert rec_b["score"] > 0.0

    # Strict Guarantee: Feasible courier with lower reliability ranks ABOVE 99% reliable infeasible courier
    assert rec_b["score"] > rec_a["score"]

    # Attempting to assign infeasible Star Courier via API MUST fail with HTTP 400
    admin = _create_user(db, f"admin_gate_{ts}@test.com", "admin", "Admin Gate")
    headers_admin = _auth_headers(admin)
    assign_resp = client.post(
        f"/api/volunteers/assignments?donation_id={donation.id}&volunteer_id={vol_a_star.id}",
        headers=headers_admin
    )
    assert assign_resp.status_code == 400
    assert "infeasible" in assign_resp.json()["detail"].lower()


# ==============================================================================
# TEST 3: Telemetry Freshness - Timestamp vs ETA Value Constraint
# ==============================================================================
def test_03_telemetry_freshness_uses_actual_timestamp_never_eta_value_alone(db: Session):
    """
    CRITICAL CONSTRAINT:
    Do not infer stale telemetry from ETA value alone.
    E.g.: current_eta_minutes = 95 does NOT prove GPS is stale.
    Must strictly inspect actual timestamp: assignment.last_location_update.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    donor = _create_user(db, f"donor_fresh_{ts}@test.com", "donor", "Donor Fresh")
    vol = _create_user(db, f"vol_fresh_{ts}@test.com", "volunteer", "Vol Fresh")

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Telemetry Test Donation",
        food_category="Cooked Food",
        quantity=20.0,
        preparation_time=now,
        expiry_time=now + timedelta(hours=4),
        pickup_address="Indiranagar",
        status="volunteer_assigned"
    )
    db.add(donation)
    db.commit()

    # Case A: Large ETA (e.g. 95 minutes), but GPS was updated just 2 minutes ago
    # -> MUST BE FRESH (is_stale == False)
    assign_recent_gps = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol.id,
        status="en_route",
        assigned_at=now - timedelta(minutes=30),
        last_location_update=now - timedelta(minutes=2), # Fresh GPS ping
        current_eta_minutes=95.0, # Large ETA does NOT imply stale telemetry!
        current_distance_km=18.0
    )
    db.add(assign_recent_gps)
    db.commit()

    freshness_a = RematchingService.check_assignment_telemetry_freshness(
        assignment=assign_recent_gps,
        reference_time=now,
        max_stale_minutes=TELEMETRY_STALE_MINUTES
    )
    assert freshness_a["is_stale"] is False
    assert freshness_a["telemetry_age_minutes"] == 2.0
    assert "fresh" in freshness_a["reason"].lower()

    # Case B: Small ETA (e.g. 10 minutes), but last GPS ping was 25 minutes ago
    # -> MUST BE STALE (is_stale == True) because threshold is 15.0 minutes
    assign_stale_gps = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol.id,
        status="en_route",
        assigned_at=now - timedelta(minutes=45),
        last_location_update=now - timedelta(minutes=25), # Stale GPS ping
        current_eta_minutes=10.0, # Small ETA cannot hide stale telemetry!
        current_distance_km=2.0
    )
    db.add(assign_stale_gps)
    db.commit()

    freshness_b = RematchingService.check_assignment_telemetry_freshness(
        assignment=assign_stale_gps,
        reference_time=now,
        max_stale_minutes=TELEMETRY_STALE_MINUTES
    )
    assert freshness_b["is_stale"] is True
    assert freshness_b["telemetry_age_minutes"] == 25.0
    assert "stale" in freshness_b["reason"].lower()


# ==============================================================================
# TEST 4: Stale Telemetry Triggers Automated Dynamic Rematch Flow
# ==============================================================================
def test_04_stale_telemetry_triggers_automated_dynamic_rematch(db: Session, client: TestClient):
    """
    REMATCH FLOW ON STALE TELEMETRY:
    Active Assignment -> Telemetry check -> Stale (> 15m) -> Rematch ->
    Find feasible backup candidates -> Assign replacement -> Mark old reassigned -> Record history.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    donor = _create_user(db, f"donor_stale_{ts}@test.com", "donor", "Donor Stale", latitude=12.9716, longitude=77.5946)
    vol_old = _create_user(db, f"vol_old_{ts}@test.com", "volunteer", "Vol Stale Old", latitude=12.9716, longitude=77.5946)
    vol_backup = _create_user(db, f"vol_bak_{ts}@test.com", "volunteer", "Vol Feasible Backup", carrying_capacity=80, latitude=12.9720, longitude=77.5950)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name=f"Stale Rescue Food {ts}",
        food_category="Cooked Food",
        quantity=30.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        estimated_window_end=now + timedelta(hours=3),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        assigned_volunteer_id=vol_old.id,
        status="volunteer_assigned"
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    # Old assignment has stale telemetry: 25 minutes ago (> 15m threshold)
    old_assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol_old.id,
        status="en_route",
        assigned_at=now - timedelta(minutes=40),
        last_location_update=now - timedelta(minutes=25), # STALE
        current_eta_minutes=20.0
    )
    db.add(old_assignment)
    db.commit()
    db.refresh(old_assignment)

    headers_donor = _auth_headers(donor)

    # Call POST /api/donations/{id}/check-feasibility
    resp = client.post(
        f"/api/donations/{donation.id}/check-feasibility?auto_rematch=true",
        headers=headers_donor
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["healthy"] is False
    assert data["requires_rematch"] is True
    assert data["trigger"] == "STALE_TELEMETRY"
    assert data["telemetry"]["is_stale"] is True

    rematch_res = data["rematch_result"]
    assert rematch_res is not None
    assert rematch_res["status"] == "REMATCHED"
    assert rematch_res["new_volunteer_id"] != vol_old.id

    # Refresh DB and check state transitions
    db.refresh(donation)
    db.refresh(old_assignment)

    # 1. Old assignment marked 'reassigned' with reasons and timestamp preserved
    assert old_assignment.status == "reassigned"
    assert old_assignment.is_reassigned is True
    assert "stale" in old_assignment.reassign_reason.lower()
    assert old_assignment.reassigned_at is not None

    # 2. Donation record updated with new volunteer and rematch count incremented
    assert donation.assigned_volunteer_id != vol_old.id
    assert donation.previous_volunteer_id == vol_old.id
    assert donation.is_rematched is True
    assert donation.rematch_count == 1

    # 3. Exactly one active assignment exists (no duplicate active assignments)
    active_assignments = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
    ).all()
    assert len(active_assignments) == 1
    assert active_assignments[0].volunteer_id == donation.assigned_volunteer_id


# ==============================================================================
# TEST 5: Courier Cancellation Automatically Triggers Dynamic Rematch
# ==============================================================================
def test_05_courier_cancellation_triggers_dynamic_rematch(db: Session, client: TestClient):
    """
    COURIER CANCELLATION HANDLING:
    When an assigned courier rejects/cancels the task, dynamic rematching is automatically triggered,
    safely assigning the top feasible backup candidate.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    donor = _create_user(db, f"donor_cancel_{ts}@test.com", "donor", "Donor Cancel", latitude=12.9716, longitude=77.5946)
    vol1 = _create_user(db, f"vol_canceller_{ts}@test.com", "volunteer", "Vol Canceller", latitude=12.9716, longitude=77.5946)
    vol2_backup = _create_user(db, f"vol_replacer_{ts}@test.com", "volunteer", "Vol Replacer", carrying_capacity=80, latitude=12.9720, longitude=77.5950)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name=f"Hot Meals {ts}",
        food_category="Cooked Food",
        quantity=25.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        estimated_window_end=now + timedelta(hours=3),
        pickup_address="Brigade Road",
        latitude=12.9716,
        longitude=77.5946,
        assigned_volunteer_id=vol1.id,
        status="volunteer_assigned"
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    assign1 = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol1.id,
        status="assigned",
        assigned_at=now
    )
    db.add(assign1)
    db.commit()
    db.refresh(assign1)

    headers_vol1 = _auth_headers(vol1)

    # Vol 1 rejects assignment
    reject_resp = client.post(
        f"/api/volunteers/assignments/{assign1.id}/reject?reason=Family+emergency+cannot+fulfill",
        headers=headers_vol1
    )
    assert reject_resp.status_code == 200
    res_json = reject_resp.json()

    assert res_json["fallback_notified"] is True
    assert res_json["rematch_result"]["status"] == "REMATCHED"
    assert res_json["rematch_result"]["new_volunteer_id"] != vol1.id

    # Verify donation and assignments in DB
    db.refresh(donation)
    assert donation.assigned_volunteer_id != vol1.id
    assert donation.is_rematched is True

    # Old assignment must be retired (cancelled or reassigned) and NOT deleted
    db.expire_all()
    old_assign_check = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == assign1.id).first()
    assert old_assign_check is not None
    assert old_assign_check.status in ["cancelled", "reassigned"]


# ==============================================================================
# TEST 6: Vehicle Breakdown Automatically Triggers Dynamic Rematch
# ==============================================================================
def test_06_vehicle_breakdown_triggers_dynamic_rematch(db: Session, client: TestClient):
    """
    VEHICLE PROBLEM HANDLING:
    When a courier reports task failure due to vehicle breakdown / tyre puncture,
    system detects the vehicle issue and dispatches a feasible backup courier.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    donor = _create_user(db, f"donor_breakdown_{ts}@test.com", "donor", "Donor Breakdown", latitude=12.9716, longitude=77.5946)
    vol_stuck = _create_user(db, f"vol_stuck_{ts}@test.com", "volunteer", "Vol Flat Tyre", latitude=12.9716, longitude=77.5946)
    vol_rescue = _create_user(db, f"vol_rescue_{ts}@test.com", "volunteer", "Vol Feasible Rescue", carrying_capacity=90, latitude=12.9720, longitude=77.5950)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name=f"Breakdown Meals {ts}",
        food_category="Cooked Food",
        quantity=35.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        estimated_window_end=now + timedelta(hours=3),
        pickup_address="Koramangala",
        latitude=12.9716,
        longitude=77.5946,
        assigned_volunteer_id=vol_stuck.id,
        status="en_route"
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    assign_stuck = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol_stuck.id,
        status="en_route",
        assigned_at=now - timedelta(minutes=15)
    )
    db.add(assign_stuck)
    db.commit()

    headers_stuck = _auth_headers(vol_stuck)

    # Report task failure with vehicle issue
    fail_payload = {
        "failure_type": "pickup_failed",
        "reason": "vehicle_breakdown",
        "remarks": "Two-wheeler flat tyre and engine failure on the way to donor"
    }
    fail_resp = client.post(
        f"/api/volunteers/report-failure?donation_id={donation.id}",
        json=fail_payload,
        headers=headers_stuck
    )
    assert fail_resp.status_code == 200

    # Verify rematch was executed
    db.refresh(donation)
    assert donation.assigned_volunteer_id != vol_stuck.id
    assert donation.is_rematched is True
    assert "VEHICLE_BREAKDOWN" in donation.rematch_reason or "failure" in donation.rematch_reason.lower()


# ==============================================================================
# TEST 7: Preservation of Historical Assignment Records (No Deletions)
# ==============================================================================
def test_07_historical_assignment_records_preserved_no_deletions(db: Session, client: TestClient):
    """
    PRESERVATION OF ASSIGNMENT HISTORY:
    Ensure old assignment records are NEVER deleted upon rematching.
    GET /api/donations/{id}/rematch-status returns complete historical trace.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    donor = _create_user(db, f"donor_hist_{ts}@test.com", "donor", "Donor History", latitude=12.9716, longitude=77.5946)
    vol_1 = _create_user(db, f"vol_hist_1_{ts}@test.com", "volunteer", "Vol Hist 1", latitude=12.9716, longitude=77.5946)
    vol_2 = _create_user(db, f"vol_hist_2_{ts}@test.com", "volunteer", "Vol Hist 2", carrying_capacity=80, latitude=12.9720, longitude=77.5950)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name=f"Historical Trace Food {ts}",
        food_category="Cooked Food",
        quantity=20.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        estimated_window_end=now + timedelta(hours=3),
        pickup_address="Church Street",
        latitude=12.9716,
        longitude=77.5946,
        assigned_volunteer_id=vol_1.id,
        status="volunteer_assigned"
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    assign_1 = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol_1.id,
        status="assigned",
        assigned_at=now - timedelta(minutes=30)
    )
    db.add(assign_1)
    db.commit()

    # Trigger rematch
    headers_donor = _auth_headers(donor)
    rematch_req = client.post(
        f"/api/donations/{donation.id}/rematch",
        json={"reason": "Initial courier stuck in severe gridlock; re-optimizing route"},
        headers=headers_donor
    )
    assert rematch_req.status_code == 200

    # Query rematch status endpoint
    status_resp = client.get(
        f"/api/donations/{donation.id}/rematch-status",
        headers=headers_donor
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()

    assert status_data["is_rematched"] is True
    assert status_data["rematch_count"] == 1
    assert status_data["current_volunteer_id"] != vol_1.id
    assert status_data["previous_volunteer_id"] == vol_1.id

    # Verify history records list
    history_records = status_data["assignments_history"]
    assert len(history_records) >= 2

    # Old assignment record must exist with is_reassigned=True
    reassigned_entries = [h for h in history_records if h["volunteer_id"] == vol_1.id]
    assert len(reassigned_entries) == 1
    assert reassigned_entries[0]["is_reassigned"] is True
    assert reassigned_entries[0]["status"] == "reassigned"
    assert "gridlock" in reassigned_entries[0]["reassign_reason"].lower()

    # New assignment record must exist with status='assigned'
    new_entries = [h for h in history_records if h["volunteer_id"] == status_data["current_volunteer_id"]]
    assert len(new_entries) == 1
    assert new_entries[0]["status"] == "assigned"
    assert new_entries[0]["is_reassigned"] is False


# ==============================================================================
# TEST 8: Trilingual Non-Blaming Notifications Dispatched
# ==============================================================================
def test_08_trilingual_non_blaming_notifications(db: Session, client: TestClient):
    """
    TRILINGUAL & NON-BLAMING NOTIFICATIONS:
    Rematching notifications must support preferred languages (English, Tamil, Hindi)
    and use non-blaming, privacy-safe language regarding couriers.
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    # Donor preferred language: Tamil ('ta')
    donor_ta = _create_user(
        db, f"donor_ta_{ts}@test.com", "donor", "Tamil Donor",
        preferred_language="ta",
        latitude=12.9716, longitude=77.5946
    )

    # Vol 1 preferred language: Hindi ('hi')
    vol1_hi = _create_user(
        db, f"vol_hi_{ts}@test.com", "volunteer", "Hindi Volunteer",
        preferred_language="hi",
        latitude=12.9716, longitude=77.5946
    )

    # Vol 2 preferred language: English ('en')
    vol2_en = _create_user(
        db, f"vol_en_{ts}@test.com", "volunteer", "English Volunteer",
        preferred_language="en",
        carrying_capacity=80,
        latitude=12.9720, longitude=77.5950
    )

    donation = FoodDonation(
        donor_id=donor_ta.id,
        food_name=f"Multilingual Food {ts}",
        food_category="Cooked Food",
        quantity=20.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        estimated_window_end=now + timedelta(hours=3),
        pickup_address="Jayanagar",
        latitude=12.9716,
        longitude=77.5946,
        assigned_volunteer_id=vol1_hi.id,
        status="volunteer_assigned"
    )
    db.add(donation)
    db.commit()

    assign1 = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol1_hi.id,
        status="assigned",
        assigned_at=now
    )
    db.add(assign1)
    db.commit()

    # Trigger rematch
    headers = _auth_headers(donor_ta)
    rematch_resp = client.post(
        f"/api/donations/{donation.id}/rematch",
        json={"reason": "Route optimization"},
        headers=headers
    )
    assert rematch_resp.status_code == 200

    # 1. Check Donor Notification (Tamil)
    donor_notif = db.query(Notification).filter(
        Notification.user_id == donor_ta.id,
        Notification.related_donation_id == donation.id
    ).order_by(Notification.id.desc()).first()
    assert donor_notif is not None
    # Must contain Tamil characters and non-blaming phrasing
    assert "மீட்பு" in donor_notif.message or "மறுசீரமைக்கப்படுகிறது" in donor_notif.message

    # 2. Check Old Courier Notification (Hindi)
    vol1_notif = db.query(Notification).filter(
        Notification.user_id == vol1_hi.id,
        Notification.related_donation_id == donation.id
    ).order_by(Notification.id.desc()).first()
    assert vol1_notif is not None
    # Must contain Hindi text and non-blaming phrasing ("समय सीमा बनाए रखने के लिए")
    assert "बनाए रखने" in vol1_notif.message or "असाइन" in vol1_notif.message or "पिकअप" in vol1_notif.message

    # 3. Check New Courier Notification
    new_vol_id = rematch_resp.json()["new_volunteer_id"]
    new_vol_notif = db.query(Notification).filter(
        Notification.user_id == new_vol_id,
        Notification.related_donation_id == donation.id
    ).order_by(Notification.id.desc()).first()
    assert new_vol_notif is not None
    assert "rescue task assigned" in new_vol_notif.message.lower() or "மீட்பு" in new_vol_notif.message or "बचाव" in new_vol_notif.message
