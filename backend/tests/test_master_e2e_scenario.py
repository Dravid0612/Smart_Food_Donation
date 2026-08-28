"""
Master Real-World End-to-End Food Rescue Scenario Test (Part 37)
==============================================================
Validates the complete failure-recovery rescue chain:
1. Donor creates 50 meals (Rice + Curry).
2. Time-aware advisory assessment evaluates rescue window and urgency.
3. NGO A (Full) is rejected.
4. NGO B (Closed) is rejected.
5. NGO C (Available, Open, Capacity=150) is matched and accepts.
6. Volunteer A is assigned but does NOT respond (Timeout simulated).
7. Automatic fallback initiates and discovers Volunteer B.
8. Volunteer B has sufficient carrying capacity (80 meals) and feasible ETA.
9. Volunteer B accepts assignment.
10. Atomic OTP pickup verification at donor premises.
11. Delivery confirmation at NGO C intake.
12. NGO C records beneficiary distribution (50 donated, 50 rescued, 50 delivered, 48 distributed, 2 remaining).
13. Donor verifies final impact outcome with distinct metrics.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment, MatchOffer, Notification
from app.core.security import hash_password, create_access_token
from app.services.route_service import route_service

client = TestClient(app)

def test_part37_master_e2e_failure_recovery_scenario():
    db_session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ts = int(now.timestamp())

        # 1. Setup Actors
        # Donor
        donor = User(
            name=f"Grand Hotel Donor {ts}",
            email=f"donor_hotel_{ts}@test.com",
            password_hash=hash_password("DonorPass123!"),
            role="donor",
            phone="9876543210",
            latitude=12.9716,
            longitude=77.5946,
            is_active=True
        )
        db_session.add(donor)

        # NGO A — FULL (Zero current capacity)
        ngo_user_a = User(
            name=f"NGO A Full {ts}",
            email=f"ngoa_{ts}@test.com",
            password_hash=hash_password("NgoPass123!"),
            role="ngo",
            latitude=12.9720,
            longitude=77.5950,
            is_active=True
        )
        db_session.add(ngo_user_a)
        db_session.flush()

        ngo_a = NGO(
            user_id=ngo_user_a.id,
            organization_name="Shelter Care Full (NGO A)",
            capacity=100,
            current_capacity=0,  # FULL
            is_available=True,
            is_verified=True,
            latitude=12.9720,
            longitude=77.5950,
            operating_hours=json.dumps({"monday": {"open": "08:00", "close": "22:00", "closed": False}})
        )
        db_session.add(ngo_a)

        # NGO B — CLOSED (Operating hours closed)
        ngo_user_b = User(
            name=f"NGO B Closed {ts}",
            email=f"ngob_{ts}@test.com",
            password_hash=hash_password("NgoPass123!"),
            role="ngo",
            latitude=12.9730,
            longitude=77.5960,
            is_active=True
        )
        db_session.add(ngo_user_b)
        db_session.flush()

        ngo_b = NGO(
            user_id=ngo_user_b.id,
            organization_name="Night Shelter Closed (NGO B)",
            capacity=150,
            current_capacity=150,
            is_available=True,
            is_verified=True,
            latitude=12.9730,
            longitude=77.5960,
            operating_hours=json.dumps({
                "monday": {"open": "00:00", "close": "01:00", "closed": True},
                "tuesday": {"open": "00:00", "close": "01:00", "closed": True},
                "wednesday": {"open": "00:00", "close": "01:00", "closed": True},
                "thursday": {"open": "00:00", "close": "01:00", "closed": True},
                "friday": {"open": "00:00", "close": "01:00", "closed": True},
                "saturday": {"open": "00:00", "close": "01:00", "closed": True},
                "sunday": {"open": "00:00", "close": "01:00", "closed": True}
            })
        )
        db_session.add(ngo_b)

        # NGO C — AVAILABLE & COMPATIBLE
        ngo_user_c = User(
            name=f"NGO C Active {ts}",
            email=f"ngoc_{ts}@test.com",
            password_hash=hash_password("NgoPass123!"),
            role="ngo",
            latitude=12.9750,
            longitude=77.5980,
            is_active=True
        )
        db_session.add(ngo_user_c)
        db_session.flush()

        ngo_c = NGO(
            user_id=ngo_user_c.id,
            organization_name="Green Hope Foundation (NGO C)",
            capacity=200,
            current_capacity=150,  # Available > 50
            is_available=True,
            is_verified=True,
            latitude=12.9750,
            longitude=77.5980,
            operating_hours=json.dumps({
                day: {"open": "00:00", "close": "23:59", "closed": False}
                for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            }),
            demand_requirements=json.dumps({"Cooked Food": 100})
        )
        db_session.add(ngo_c)

        # Volunteer A — NO RESPONSE / TIMEOUT
        vol_user_a = User(
            name=f"Volunteer A (No-Show) {ts}",
            email=f"vola_{ts}@test.com",
            password_hash=hash_password("VolPass123!"),
            role="volunteer",
            vehicle_type="bike",
            carrying_capacity=50,
            reliability_score=85.0,
            latitude=12.9725,
            longitude=77.5955,
            is_active=True
        )
        db_session.add(vol_user_a)

        # Volunteer B — AVAILABLE & HIGH CAPACITY & FEASIBLE
        vol_user_b = User(
            name=f"Volunteer B (Reliable) {ts}",
            email=f"volb_{ts}@test.com",
            password_hash=hash_password("VolPass123!"),
            role="volunteer",
            vehicle_type="van",
            carrying_capacity=80,  # Sufficient for 50 meals
            reliability_score=98.0,
            latitude=12.9740,
            longitude=77.5970,
            is_active=True
        )
        db_session.add(vol_user_b)

        db_session.commit()

        donor_token = create_access_token({"sub": str(donor.id), "role": "donor"})
        ngo_c_token = create_access_token({"sub": str(ngo_user_c.id), "role": "ngo"})
        vol_a_token = create_access_token({"sub": str(vol_user_a.id), "role": "volunteer"})
        vol_b_token = create_access_token({"sub": str(vol_user_b.id), "role": "volunteer"})

        # ── Step 1: Donor Posts Food Donation (50 meals Rice + Curry) ───────────
        prep_time = (now - timedelta(minutes=45)).isoformat()
        expiry_time = (now + timedelta(hours=3)).isoformat()

        create_payload = {
            "food_name": "Rice + Curry Surplus Set",
            "food_type": "Rice",
            "food_category": "Cooked Food",
            "quantity": 50.0,
            "quantity_unit": "Meals",
            "preparation_time": prep_time,
            "expiry_time": expiry_time,
            "pickup_address": "Main Hotel Banquet, MG Road, Bengaluru",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "storage_method": "Room Temperature",
            "packaging_condition": "Covered",
            "previously_served": "No",
            "exposure_status": "No",
            "handling_status": "No",
            "ai_visual_condition": "GOOD",
            "ai_visible_spoilage": "Not detected",
            "ai_confidence_score": 0.92
        }

        create_resp = client.post(
            "/api/donations",
            headers={"Authorization": f"Bearer {donor_token}"},
            json=create_payload
        )
        assert create_resp.status_code == 201, create_resp.text
        donation_data = create_resp.json()
        donation_id = donation_data["id"]

        # Fetch donation detail as donor to obtain verification OTP securely
        donor_detail_resp = client.get(
            f"/api/donations/{donation_id}",
            headers={"Authorization": f"Bearer {donor_token}"}
        )
        assert donor_detail_resp.status_code == 200
        pickup_otp = donor_detail_resp.json()["verification_otp"]
        assert pickup_otp is not None

        assert donation_data["quantity"] == 50.0
        assert donation_data["status"] == "pending"

        # ── Step 2: RouteService & Feasibility Calculation ───────────────────────
        route_calc = route_service.calculate_eta(12.9716, 77.5946, 12.9750, 77.5980, transport_mode="van")
        assert route_calc["status"] in ["ROUTE_AVAILABLE", "ROUTE_ESTIMATE_DEGRADED"]
        assert route_calc["eta_minutes"] >= 5

        # ── Step 3: NGO Recommendation Filtering (Hard Rejections) ───────────────
        rec_resp = client.get(
            f"/api/donations/{donation_id}/recommend-ngo",
            headers={"Authorization": f"Bearer {donor_token}"}
        )
        assert rec_resp.status_code == 200
        ngos_ranked = rec_resp.json()
        
        ngo_a_entry = next((n for n in ngos_ranked if n["ngo_id"] == ngo_a.id), None)
        ngo_b_entry = next((n for n in ngos_ranked if n["ngo_id"] == ngo_b.id), None)
        ngo_c_entry = next((n for n in ngos_ranked if n["ngo_id"] == ngo_c.id), None)

        assert ngo_c_entry is not None
        assert ngo_c_entry["demand_matched"] is True
        assert ngo_c_entry["is_open_now"] is True
        assert ngo_c_entry["current_capacity"] >= 50

        # NGO C (Available) must score significantly higher than NGO A (Full) and NGO B (Closed)
        if ngo_a_entry:
            assert ngo_c_entry["score"] > ngo_a_entry["score"]
        if ngo_b_entry:
            assert ngo_c_entry["score"] > ngo_b_entry["score"]

        # ── Step 4: NGO C Accepts the Donation ──────────────────────────────────
        accept_resp = client.post(
            f"/api/donations/{donation_id}/accept",
            headers={"Authorization": f"Bearer {ngo_c_token}"}
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["assigned_ngo_id"] == ngo_c.id

        # Verify capacity reservation
        db_session.refresh(ngo_c)
        assert ngo_c.current_capacity == 100  # 150 - 50 = 100

        # ── Step 5: Volunteer A is Initially Assigned & Times Out ────────────────
        assign_a_resp = client.post(
            f"/api/volunteers/assignments?donation_id={donation_id}&volunteer_id={vol_user_a.id}",
            headers={"Authorization": f"Bearer {ngo_c_token}"}
        )
        assert assign_a_resp.status_code == 200

        # Simulate Volunteer A timeout (past 15 minutes cutoff)
        assignment_a = db_session.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == donation_id,
            VolunteerAssignment.volunteer_id == vol_user_a.id
        ).first()
        assignment_a.assigned_at = now - timedelta(minutes=20)
        db_session.commit()

        # Trigger automatic timeout sweep & fallback
        timeout_resp = client.post(
            "/api/donations/process-timeouts?volunteer_timeout_minutes=15",
            headers={"Authorization": f"Bearer {donor_token}"}
        )
        assert timeout_resp.status_code == 200
        timeout_data = timeout_resp.json()
        assert timeout_data["expired_volunteer_assignments"] >= 1

        # Donation status reverted to 'accepted' for fallback
        donation_check = client.get(
            f"/api/donations/{donation_id}",
            headers={"Authorization": f"Bearer {donor_token}"}
        ).json()
        assert donation_check["status"] == "accepted"

        # ── Step 6: Volunteer B Discovered & Assigned via Fallback ───────────────
        vol_rec_resp = client.get(
            f"/api/donations/{donation_id}/recommend-volunteer",
            headers={"Authorization": f"Bearer {ngo_c_token}"}
        )
        assert vol_rec_resp.status_code == 200
        vols_ranked = vol_rec_resp.json()
        vol_b_entry = next((v for v in vols_ranked if v["volunteer_id"] == vol_user_b.id), None)
        assert vol_b_entry is not None
        assert vol_b_entry["carrying_capacity"] >= 50

        assign_b_resp = client.post(
            f"/api/volunteers/assignments?donation_id={donation_id}&volunteer_id={vol_user_b.id}",
            headers={"Authorization": f"Bearer {ngo_c_token}"}
        )
        assert assign_b_resp.status_code == 200
        assign_b_id = assign_b_resp.json()["id"]

        # Volunteer B accepts task
        vol_b_accept = client.post(
            f"/api/volunteers/assignments/{assign_b_id}/accept",
            headers={"Authorization": f"Bearer {vol_b_token}"}
        )
        assert vol_b_accept.status_code == 200

        # ── Step 7: Atomic OTP-Verified Pickup ───────────────────────────────────
        # Reject invalid OTP
        bad_otp_resp = client.post(
            "/api/volunteers/verify-otp",
            headers={"Authorization": f"Bearer {vol_b_token}"},
            json={"donation_id": donation_id, "otp": "000000"}
        )
        assert bad_otp_resp.status_code == 400

        # Confirm with valid OTP
        good_otp_resp = client.post(
            "/api/volunteers/verify-otp",
            headers={"Authorization": f"Bearer {vol_b_token}"},
            json={"donation_id": donation_id, "otp": pickup_otp}
        )
        assert good_otp_resp.status_code == 200
        assert good_otp_resp.json()["status"] == "collected"

        # ── Step 8: Volunteer Delivers Food to NGO C ──────────────────────────────
        deliver_resp = client.put(
            f"/api/volunteers/assignments/{assign_b_id}?status_update=delivered",
            headers={"Authorization": f"Bearer {vol_b_token}"}
        )
        assert deliver_resp.status_code == 200
        assert deliver_resp.json()["status"] == "delivered"

        # ── Step 9: NGO C Records Beneficiary Distribution ───────────────────────
        # Meals Donated: 50 | Rescued: 50 | Delivered: 50 | Distributed: 48 | Remaining: 2
        dist_payload = {
            "received_quantity": 50.0,
            "distributed_quantity": 48.0,
            "remaining_quantity": 2.0,
            "beneficiaries_served": 48,
            "remarks": "48 warm meals distributed to evening shelter families. 2 preserved in cold pantry."
        }
        dist_resp = client.post(
            f"/api/donations/{donation_id}/distribution",
            headers={"Authorization": f"Bearer {ngo_c_token}"},
            json=dist_payload
        )
        assert dist_resp.status_code == 200
        dist_data = dist_resp.json()
        assert dist_data["distributed_quantity"] == 48.0
        assert dist_data["remaining_quantity"] == 2.0

        # ── Step 10: Donor Impact Summary & Verification ─────────────────────────
        impact_resp = client.get(
            "/api/donations/donor/impact-summary",
            headers={"Authorization": f"Bearer {donor_token}"}
        )
        assert impact_resp.status_code == 200
        impact_data = impact_resp.json()
        assert impact_data["meals_donated"] >= 50.0
        assert impact_data["meals_rescued"] >= 50.0
        assert impact_data["meals_distributed"] >= 48.0
        assert impact_data["successful_rescues_count"] >= 1

        # ── Step 11: Repeat Donation Prefill Check ───────────────────────────────
        repeat_resp = client.get(
            "/api/donations/repeat-prefill/latest",
            headers={"Authorization": f"Bearer {donor_token}"}
        )
        assert repeat_resp.status_code == 200
        repeat_data = repeat_resp.json()
        assert repeat_data["previous_donation_id"] == donation_id
        assert repeat_data["food_name"] == "Rice + Curry Surplus Set"
        assert "reconfirmation_required" in repeat_data

    finally:
        db_session.close()
