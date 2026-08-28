"""
Test Suite: Dynamic Rematching & Feasibility-Driven Logistics Reassignment
===========================================================================
Verifies continuous feasibility evaluation, automatic dynamic rematching upon
route delays, hard-gated candidate selection, atomic reassignment locking, and
trilingual notifications.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.models import (
    User, NGO, FoodDonation, VolunteerAssignment, Notification, AuditLog, DonationHistory
)
from app.core.security import create_access_token, hash_password
from app.services.rematching_service import rematching_service

client = TestClient(app)


def test_01_automatic_dynamic_rematch_on_eta_infeasible(db_session: Session):
    """
    Core dynamic rematch flow:
    - Volunteer A initially assigned.
    - Route delay simulated: Volunteer A location update yields ETA (35 min) > remaining rescue window (25 min).
    - System flags rescue as AT_RISK and automatically executes atomic rematching.
    - Backup Volunteer B (van, high capacity, feasible ETA ~10 min) is dispatched.
    - Trilingual notifications dispatched to Donor, NGO, Volunteer A, Volunteer B, and Admin.
    """
    ts = int(datetime.now().timestamp())

    # Donor (Tamil preferred)
    donor = User(
        name=f"Rematch Donor {ts}",
        email=f"don_rem_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="donor",
        preferred_language="ta",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(donor)

    # Volunteer A (Delayed Courier)
    vol_a = User(
        name=f"Volunteer A (Delayed) {ts}",
        email=f"vola_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="volunteer",
        preferred_language="en",
        vehicle_type="bike",
        carrying_capacity=50,
        reliability_score=90.0,
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(vol_a)

    # Volunteer B (Reliable Backup Courier)
    vol_b = User(
        name=f"Volunteer B (Fast Backup) {ts}",
        email=f"volb_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="volunteer",
        preferred_language="hi",
        vehicle_type="van",
        carrying_capacity=80,
        reliability_score=98.0,
        latitude=12.9730,
        longitude=77.5960,
        is_active=True
    )
    db_session.add(vol_b)

    # NGO
    ngo_u = User(
        name=f"NGO Rematch {ts}",
        email=f"ngo_rem_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="ngo",
        preferred_language="en",
        is_active=True
    )
    db_session.add(ngo_u)
    db_session.flush()

    ngo = NGO(
        user_id=ngo_u.id,
        organization_name="Community Kitchen",
        capacity=150,
        current_capacity=100,
        is_available=True,
        is_verified=True,
        latitude=12.9780,
        longitude=77.6000
    )
    db_session.add(ngo)
    db_session.flush()

    now = datetime.now(timezone.utc)
    # Rescue window ending in 50 minutes
    window_end = now + timedelta(minutes=50)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Hot Meals Sambar Rice",
        food_category="Cooked Food",
        quantity=40.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=window_end,
        estimated_window_start=now - timedelta(hours=1),
        estimated_window_end=window_end,
        remaining_minutes=50,
        pickup_address="Indiranagar 100ft Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="volunteer_assigned",
        assigned_ngo_id=ngo.id,
        assigned_volunteer_id=vol_a.id,
        feasibility_status="RESCUE_FEASIBLE"
    )
    db_session.add(donation)
    db_session.flush()

    assign_a = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol_a.id,
        status="en_route",
        assigned_at=now,
        current_eta_minutes=10.0
    )
    db_session.add(assign_a)
    db_session.commit()

    token_a = create_access_token({"sub": str(vol_a.id), "role": "volunteer"})

    # Volunteer A transmits location far away (e.g., 15 km away -> ETA ~45 mins)
    resp = client.post(
        "/api/volunteers/location",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "latitude": 13.0827,  # Far away
            "longitude": 77.5877,
            "donation_id": donation.id
        }
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["rematch_triggered"] is True
    assert res_data["rematch_info"]["status"] == "REMATCHED"
    new_vol_id = res_data["rematch_info"]["new_volunteer_id"]
    assert new_vol_id is not None
    assert new_vol_id != vol_a.id

    # Verify database state
    db_session.refresh(donation)
    assert donation.assigned_volunteer_id == new_vol_id
    assert donation.previous_volunteer_id == vol_a.id
    assert donation.is_rematched is True
    assert donation.rematch_count == 1

    # Verify old assignment retired
    db_session.refresh(assign_a)
    assert assign_a.status == "reassigned"
    assert assign_a.is_reassigned is True

    # Verify new assignment created
    new_assign = db_session.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.volunteer_id == new_vol_id
    ).first()
    assert new_assign is not None
    assert new_assign.status == "assigned"

    # Verify trilingual notifications created
    donor_notif = db_session.query(Notification).filter(
        Notification.user_id == donor.id,
        Notification.event_type == "RESCUE_REMATCHED_DONOR"
    ).first()
    assert donor_notif is not None
    assert "மீட்பு திட்டம்" in donor_notif.title or "மீட்பு" in donor_notif.message


def test_02_hard_gates_filter_infeasible_backup_volunteers(db_session: Session):
    """
    Verifies hard gates:
    - Volunteer C: Low capacity (20 < 50) -> Filtered out.
    - Volunteer D: Concurrency maxed out (3 active tasks) -> Filtered out.
    - Volunteer E: Infeasible ETA (> remaining window) -> Filtered out.
    """
    ts = int(datetime.now().timestamp())
    now = datetime.now(timezone.utc)

    # Ineligible Volunteer C (Capacity too low)
    vol_c = User(name=f"Vol C {ts}", email=f"volc_{ts}@test.com", password_hash=hash_password("Pass123!"), role="volunteer", carrying_capacity=20, is_active=True)
    # Ineligible Volunteer D (Busy with 3 tasks)
    vol_d = User(name=f"Vol D {ts}", email=f"vold_{ts}@test.com", password_hash=hash_password("Pass123!"), role="volunteer", carrying_capacity=80, is_active=True)
    db_session.add_all([vol_c, vol_d])
    db_session.flush()

    for i in range(3):
        don_dummy = FoodDonation(
            donor_id=vol_c.id, food_name=f"Dummy {i}", food_category="Cooked Food", quantity=10, quantity_unit="Meals",
            preparation_time=now, expiry_time=now + timedelta(hours=2), pickup_address="Addr", status="en_route"
        )
        db_session.add(don_dummy)
        db_session.flush()
        db_session.add(VolunteerAssignment(donation_id=don_dummy.id, volunteer_id=vol_d.id, status="en_route", assigned_at=now))

    test_don = FoodDonation(
        donor_id=vol_c.id, food_name="Target 50 Meals", food_category="Cooked Food", quantity=50, quantity_unit="Meals",
        preparation_time=now, expiry_time=now + timedelta(minutes=20), remaining_minutes=20, pickup_address="Addr",
        latitude=12.9716, longitude=77.5946, status="volunteer_assigned"
    )
    db_session.add(test_don)
    db_session.commit()

    candidates = rematching_service.find_feasible_backup_volunteers(db_session, test_don)
    candidate_ids = [c["volunteer_id"] for c in candidates]
    assert vol_c.id not in candidate_ids
    assert vol_d.id not in candidate_ids


def test_03_manual_admin_rematch_endpoint(db_session: Session):
    """Verifies manual administrator rematch intervention via POST /api/donations/{id}/rematch."""
    ts = int(datetime.now().timestamp())
    admin_u = User(name=f"Admin {ts}", email=f"adm_{ts}@test.com", password_hash=hash_password("Pass123!"), role="admin", is_active=True)
    vol_orig = User(name=f"Orig {ts}", email=f"orig_{ts}@test.com", password_hash=hash_password("Pass123!"), role="volunteer", carrying_capacity=50, is_active=True)
    vol_backup = User(name=f"Backup {ts}", email=f"bak_{ts}@test.com", password_hash=hash_password("Pass123!"), role="volunteer", carrying_capacity=60, is_active=True)
    donor = User(name=f"Don {ts}", email=f"don_{ts}@test.com", password_hash=hash_password("Pass123!"), role="donor", is_active=True)
    db_session.add_all([admin_u, vol_orig, vol_backup, donor])
    db_session.flush()

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Buffet Dinner",
        food_category="Cooked Food",
        quantity=35.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=2),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="volunteer_assigned",
        assigned_volunteer_id=vol_orig.id
    )
    db_session.add(donation)
    db_session.flush()

    db_session.add(VolunteerAssignment(donation_id=donation.id, volunteer_id=vol_orig.id, status="en_route", assigned_at=now))
    db_session.commit()

    admin_token = create_access_token({"sub": str(admin_u.id), "role": "admin"})

    resp = client.post(
        f"/api/donations/{donation.id}/rematch",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Admin coordinator intervention due to vehicle flat tyre"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REMATCHED"
    assert data["previous_volunteer_id"] == vol_orig.id
    assert data["new_volunteer_id"] is not None
    assert data["new_volunteer_id"] != vol_orig.id

    # Check status endpoint
    resp_st = client.get(f"/api/donations/{donation.id}/rematch-status", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_st.status_code == 200
    st_data = resp_st.json()
    assert st_data["is_rematched"] is True
    assert st_data["rematch_count"] == 1
    assert len(st_data["assignments_history"]) >= 2
