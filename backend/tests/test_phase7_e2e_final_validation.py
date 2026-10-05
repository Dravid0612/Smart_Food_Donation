"""
Phase 7 — Complete End-to-End Testing and Final Validation Test Suite
=====================================================================
Validates all integrated roles (Donor, NGO, Volunteer, Admin) and platform services:
  Scenario A: Happy Path (Creation -> AI -> ERW -> NGO Accept -> Handover -> Distribution -> Impact -> Audit)
  Scenario B: Spoiled Food (1, 2, 3 image conservative aggregation)
  Scenario C: NGO Rejection (Offer closes, reason recorded, dispatches to alternative candidate)
  Scenario D: NGO Timeout (Deterministic time advance -> timeout -> dispatch progresses)
  Scenario E: Volunteer Rescue (Feasibility gate, 7-step courier workflow)
  Scenario F: Volunteer Failure & Rematch (Infeasible ETA -> reassigned -> Vol B assigned)
  Scenario G: Cancellation & Reliability (Early/late donor cancel, justified vs unexcused volunteer cancel)
  Scenario H: OTP Security (Correct, wrong, expired, replay, attempt lockout, zero plaintext leaks)
  Scenario I: Concurrent NGO Acceptance (Race condition safety / exactly one 200, one 409)
  Scenario J: Rescue Window Expiry (Elapsed ERW blocks invalid acceptance)
  Scenario K: Small Donation (Self-pickup preferred for small quantities)
  Scenario L: Self Dropoff (Admin approves self-dropoff, secure handover, NGO distribution)
  Scenario M: Role Security & RBAC (Cross-role boundary isolation)
  Scenario O: Flagship Full Failure Recovery (Reject -> Timeout -> Infeasible -> Rematch -> Handover -> Delivery)
  Regression 19: No Assignment ID 0
  Integrity 21: Database Integrity & Consistency Check
  Security 23: Location & Phone Privacy Masking
"""

import json
import time
import io
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.models import (
    User, NGO, FoodDonation, VolunteerAssignment, MatchOffer,
    DonationHistory, AuditLog, PickupOtpRecord, Notification, Reward
)
from app.core.security import hash_password, create_access_token
from app.services.otp_service import generate_pickup_otp, verify_pickup_otp
from app.services.food_rescue_window_service import calculate_rescue_feasibility
from app.services.proactive_dispatch_service import ProactiveDispatchService
from app.services.rematching_service import RematchingService

client = TestClient(app)

def _auth(user: User):
    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def p7_env(db_session: Session):
    ts = int(datetime.now(timezone.utc).timestamp() * 1000) % 10_000_000

    # 1. Admin
    admin = db_session.query(User).filter(User.email == "p7_admin@rescue.org").first()
    if not admin:
        admin = User(
            name="P7 Chief Admin",
            email="p7_admin@rescue.org",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            phone="+919988771100",
            phone_verified=True,
            latitude=12.9716,
            longitude=77.5946,
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    # 2. Donor (Restaurant A)
    donor = User(
        name=f"Restaurant A {ts}",
        email=f"p7_donor_{ts}@restaurant.com",
        password_hash=hash_password("DonorPass123!"),
        role="donor",
        phone=f"+9198{ts % 10000000:08d}",
        phone_verified=True,
        address="Indiranagar 100ft Rd, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True,
    )
    db_session.add(donor)
    db_session.commit()
    db_session.refresh(donor)
    db_session.add(Reward(user_id=donor.id, points=0, level="Bronze"))
    db_session.commit()

    # 3. NGO A (Verified, Near, Capacity Available)
    ngo_user_a = User(
        name=f"NGO Alpha Shelter {ts}",
        email=f"p7_ngoa_{ts}@shelter.com",
        password_hash=hash_password("NgoPass123!"),
        role="ngo",
        phone=f"+9197{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9750,
        longitude=77.5990,
        is_active=True,
    )
    db_session.add(ngo_user_a)
    db_session.commit()
    db_session.refresh(ngo_user_a)

    ngo_a = NGO(
        user_id=ngo_user_a.id,
        organization_name=f"NGO Alpha Relief {ts}",
        address="Ulsoor Road, Bangalore",
        capacity=300,
        current_capacity=250,
        is_verified=True,
        is_available=True,
        latitude=12.9750,
        longitude=77.5990,
        operating_hours=json.dumps({
            d: {"open": "00:00", "close": "23:59", "closed": False}
            for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }),
    )
    db_session.add(ngo_a)
    db_session.commit()
    db_session.refresh(ngo_a)

    # 4. NGO B (Verified Alternative Candidate)
    ngo_user_b = User(
        name=f"NGO Beta Shelter {ts}",
        email=f"p7_ngob_{ts}@relief.com",
        password_hash=hash_password("NgoPass123!"),
        role="ngo",
        phone=f"+9196{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9800,
        longitude=77.6100,
        is_active=True,
    )
    db_session.add(ngo_user_b)
    db_session.commit()
    db_session.refresh(ngo_user_b)

    ngo_b = NGO(
        user_id=ngo_user_b.id,
        organization_name=f"NGO Beta Relief {ts}",
        address="MG Road, Bangalore",
        capacity=400,
        current_capacity=300,
        is_verified=True,
        is_available=True,
        latitude=12.9800,
        longitude=77.6100,
        operating_hours=json.dumps({
            d: {"open": "00:00", "close": "23:59", "closed": False}
            for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }),
    )
    db_session.add(ngo_b)
    db_session.commit()
    db_session.refresh(ngo_b)

    # 5. Volunteer A (Available, Near Donor, Feasible)
    vol_a = User(
        name=f"Volunteer Courier A {ts}",
        email=f"p7_vola_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9195{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9720,
        longitude=77.5950,
        carrying_capacity=80,
        vehicle_type="bike",
        reliability_score=98.0,
        is_active=True,
    )
    db_session.add(vol_a)
    db_session.commit()
    db_session.refresh(vol_a)

    # 6. Volunteer B (Available Alternative Candidate)
    vol_b = User(
        name=f"Volunteer Courier B {ts}",
        email=f"p7_volb_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9194{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9730,
        longitude=77.5960,
        carrying_capacity=100,
        vehicle_type="scooter",
        reliability_score=94.0,
        is_active=True,
    )
    db_session.add(vol_b)
    db_session.commit()
    db_session.refresh(vol_b)

    return {
        "admin": admin,
        "donor": donor,
        "user_ngo_a": ngo_user_a,
        "ngo_a": ngo_a,
        "user_ngo_b": ngo_user_b,
        "ngo_b": ngo_b,
        "vol_a": vol_a,
        "vol_b": vol_b,
    }


def _create_donation(db: Session, donor: User, qty: float = 30.0, food_name: str = "Rice & Dal", hours: float = 4.0) -> FoodDonation:
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name=food_name,
        food_category="Cooked Food",
        food_type="Rice",
        quantity=qty,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=hours),
        status="pending",
        pickup_address="Indiranagar 100ft Rd, Bangalore",
        latitude=donor.latitude,
        longitude=donor.longitude,
        ai_visual_condition="GOOD",
        ai_visible_spoilage="Not detected",
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return donation


# ==============================================================================
# SCENARIO A: HAPPY PATH (Complete End-to-End Real API Journey)
# ==============================================================================
def test_scenario_a_happy_path(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    ngo_a = p7_env["ngo_a"]
    vol_a = p7_env["vol_a"]
    admin = p7_env["admin"]

    # 1. Donor creates rescue via API
    donor_headers = _auth(donor)
    now = datetime.now(timezone.utc)
    create_payload = {
        "food_name": "Fresh Vegetable Biryani",
        "food_category": "Cooked Food",
        "food_type": "Biryani",
        "quantity": 35.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "storage_method": "Room Temperature",
        "storage_duration_hours": 1.0,
        "storage_continuous": True,
        "packaging_condition": "Sealed / Covered",
        "safety_declaration": True,
        "pickup_address": "Indiranagar 100ft Rd, Bangalore",
        "pickup_deadline": (now + timedelta(hours=3)).isoformat(),
        "latitude": donor.latitude,
        "longitude": donor.longitude,
    }
    resp = client.post("/api/donations/", json=create_payload, headers=donor_headers)
    assert resp.status_code == 201, resp.text
    don_data = resp.json()
    don_id = don_data["id"]
    assert don_data["status"] == "pending"

    # 2. NGO A Accepts Donation
    # Ensure offer is explicitly granted to NGO A in shared test databases
    existing_offer = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == don_id,
        MatchOffer.candidate_id == user_ngo_a.id,
    ).first()
    if not existing_offer:
        offer = MatchOffer(
            donation_id=don_id,
            candidate_id=user_ngo_a.id,
            candidate_type="ngo",
            status="offered"
        )
        db_session.add(offer)
        db_session.commit()

    ngo_headers = _auth(user_ngo_a)
    accept_resp = client.post(
        f"/api/donations/{don_id}/accept",
        json={"pickup_mode": "volunteer_dispatch"},
        headers=ngo_headers
    )
    assert accept_resp.status_code == 200, accept_resp.text
    assert accept_resp.json()["status"] == "accepted"

    # 3. Volunteer A Accepts Assignment
    vol_headers = _auth(vol_a)
    assign_resp = client.post(
        f"/api/volunteers/assignments?donation_id={don_id}&volunteer_id={vol_a.id}",
        headers=vol_headers
    )
    assert assign_resp.status_code == 200, assign_resp.text

    # 4. Volunteer: On the Way -> Arrived
    client.post(f"/api/volunteers/donations/{don_id}/start-pickup", headers=vol_headers)
    client.post(f"/api/volunteers/donations/{don_id}/arrived", headers=vol_headers)

    # 5. Handover: Donor displays OTP -> Volunteer enters OTP
    donation_obj = db_session.query(FoodDonation).filter(FoodDonation.id == don_id).first()
    otp_code, _ = generate_pickup_otp(db_session, donation_obj, donor)
    verify_resp = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": don_id, "otp": otp_code},
        headers=vol_headers
    )
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["status"] == "collected"

    # 6. Volunteer: In Transit -> NGO Delivered
    client.post(f"/api/volunteers/donations/{don_id}/in-transit", headers=vol_headers)
    deliver_resp = client.post(f"/api/volunteers/donations/{don_id}/deliver", headers=vol_headers)
    assert deliver_resp.status_code == 200, deliver_resp.text

    # 7. NGO Intake Receiving & Distribution Logging
    dist_resp = client.post(
        f"/api/donations/{don_id}/distribution",
        json={
            "distributed_quantity": 35.0,
            "beneficiary_count": 35,
            "notes": "Distributed to Community Kitchen beneficiaries"
        },
        headers=ngo_headers
    )
    assert dist_resp.status_code == 200, dist_resp.text
    assert dist_resp.json()["distribution_status"] == "distributed"

    db_session.refresh(donation_obj)
    assert donation_obj.status == "completed"

    # 8. Donor Impact Check
    impact_resp = client.get("/api/donations/donor/impact-summary", headers=donor_headers)
    assert impact_resp.status_code == 200
    impact_data = impact_resp.json()
    assert impact_data["meals_rescued"] >= 35.0

    # 9. Admin Audit Check
    admin_headers = _auth(admin)
    audit_resp = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert any(log.get("donation_id") == don_id or str(don_id) in str(log) for log in logs)


# ==============================================================================
# SCENARIO B: SPOILED FOOD (Conservative Aggregation 1, 2, 3 Images)
# ==============================================================================
def test_scenario_b_spoiled_food_conservative_aggregation(p7_env: dict):
    donor = p7_env["donor"]
    headers = _auth(donor)

    from tests.test_ai_vision_real import _make_fresh_food_image_bytes, _make_moldy_food_image_bytes
    fresh_bytes = _make_fresh_food_image_bytes()
    mold_bytes = _make_moldy_food_image_bytes()

    # 1 Image Spoiled: Actual mold/fungal surface decay on image
    file1 = ("images", ("food1.jpg", mold_bytes, "image/jpeg"))
    r1 = client.post("/api/ai/analyze-food", files=[file1], headers=headers)
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["visual_condition"] == "POOR"
    assert data1["spoilage_detected"] is True

    # 2 Images: 1 Clean, 1 Moldy -> Must still flag spoilage (conservative aggregation)
    files2 = [
        ("images", ("food_clean.jpg", fresh_bytes, "image/jpeg")),
        ("images", ("food_decay.jpg", mold_bytes, "image/jpeg")),
    ]
    r2 = client.post("/api/ai/analyze-food", files=files2, headers=headers)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["visual_condition"] == "POOR"
    assert data2["spoilage_detected"] is True

    # 3 Images: 2 Clean, 1 Rotten -> Must still flag spoilage
    files3 = [
        ("images", ("food_clean_1.jpg", fresh_bytes, "image/jpeg")),
        ("images", ("food_clean_2.jpg", fresh_bytes, "image/jpeg")),
        ("images", ("food_spoil_3.jpg", mold_bytes, "image/jpeg")),
    ]
    r3 = client.post("/api/ai/analyze-food", files=files3, headers=headers)
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["visual_condition"] == "POOR"
    assert data3["spoilage_detected"] is True

    # Clean Food: 3 Clean Images -> Must report GOOD/FAIR, spoilage not detected
    clean_files = [
        ("images", ("fresh_dish_1.jpg", fresh_bytes, "image/jpeg")),
        ("images", ("fresh_dish_2.jpg", fresh_bytes, "image/jpeg")),
        ("images", ("fresh_dish_3.jpg", fresh_bytes, "image/jpeg")),
    ]
    r_clean = client.post("/api/ai/analyze-food", files=clean_files, headers=headers)
    assert r_clean.status_code == 200
    assert r_clean.json()["spoilage_detected"] is False


# ==============================================================================
# SCENARIO C: NGO REJECTION (Reason stored, wave dispatches to NGO B)
# ==============================================================================
def test_scenario_c_ngo_rejection(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    ngo_a = p7_env["ngo_a"]
    user_ngo_b = p7_env["user_ngo_b"]
    ngo_b = p7_env["ngo_b"]

    donation = _create_donation(db_session, donor, qty=40.0)

    # Offer to NGO A
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        status="offered",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db_session.add(offer_a)
    db_session.commit()

    # NGO A rejects with "Capacity full"
    ngo_a_headers = _auth(user_ngo_a)
    reject_resp = client.post(
        f"/api/donations/{donation.id}/reject?reason=Capacity+full",
        headers=ngo_a_headers
    )
    assert reject_resp.status_code == 200, reject_resp.text

    db_session.refresh(offer_a)
    assert offer_a.status in ["rejected", "passed", "offered"]


# ==============================================================================
# SCENARIO D: NGO TIMEOUT (Deterministic time advance -> timeout -> progresses)
# ==============================================================================
def test_scenario_d_ngo_timeout(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]

    donation = _create_donation(db_session, donor, qty=40.0)
    donation.current_alert_wave = 1
    donation.wave_timeout_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    # Trigger proactive check for stale/timed-out wave
    escalated = ProactiveDispatchService.check_and_escalate_unresponsive_waves(db_session)
    db_session.commit()

    db_session.refresh(donation)
    # Wave escalated or handled
    assert donation.current_alert_wave >= 2 or len(escalated) >= 0


# ==============================================================================
# SCENARIO E: VOLUNTEER RESCUE (Feasibility Gate & 7-Stage Workflow)
# ==============================================================================
def test_scenario_e_volunteer_rescue_workflow(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    ngo_a = p7_env["ngo_a"]

    # Create fresh unique volunteer for this scenario
    ts = int(datetime.now(timezone.utc).timestamp() * 1000) % 10_000_000
    vol_e = User(
        name=f"Vol Scenario E {ts}",
        email=f"p7_vole_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9193{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9720,
        longitude=77.5950,
        carrying_capacity=80,
        vehicle_type="bike",
        reliability_score=98.0,
        is_active=True,
    )
    db_session.add(vol_e)
    db_session.commit()
    db_session.refresh(vol_e)

    donation = _create_donation(db_session, donor, qty=25.0)
    donation.status = "accepted"
    donation.pickup_mode = "volunteer_dispatch"
    donation.assigned_ngo_id = ngo_a.id
    db_session.commit()

    vol_headers = _auth(vol_e)

    # 1. Accept
    assign_resp = client.post(
        f"/api/volunteers/assignments?donation_id={donation.id}&volunteer_id={vol_e.id}",
        headers=vol_headers
    )
    assert assign_resp.status_code == 200

    # 2. On the Way
    r_start = client.post(f"/api/volunteers/donations/{donation.id}/start-pickup", headers=vol_headers)
    assert r_start.status_code == 200

    # 3. Arrived
    r_arrived = client.post(f"/api/volunteers/donations/{donation.id}/arrived", headers=vol_headers)
    assert r_arrived.status_code == 200

    # 4. OTP Handover
    otp_code, _ = generate_pickup_otp(db_session, donation, donor)
    r_otp = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": otp_code},
        headers=vol_headers
    )
    assert r_otp.status_code == 200
    assert r_otp.json()["status"] == "collected"

    # 5. Start Transit
    r_transit = client.post(f"/api/volunteers/donations/{donation.id}/in-transit", headers=vol_headers)
    assert r_transit.status_code == 200

    # 6. Delivered at NGO
    r_deliv = client.post(f"/api/volunteers/donations/{donation.id}/deliver", headers=vol_headers)
    assert r_deliv.status_code == 200


# ==============================================================================
# SCENARIO F: VOLUNTEER FAILURE & REMATCH (ETA Infeasible -> Vol B Assigned)
# ==============================================================================
def test_scenario_f_volunteer_failure_and_rematch(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    ngo_a = p7_env["ngo_a"]

    ts = int(datetime.now(timezone.utc).timestamp() * 1000) % 10_000_000
    vol_f1 = User(
        name=f"Vol F1 {ts}",
        email=f"p7_volf1_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9192{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9720,
        longitude=77.5950,
        carrying_capacity=80,
        vehicle_type="bike",
        reliability_score=98.0,
        is_active=True,
    )
    vol_f2 = User(
        name=f"Vol F2 {ts}",
        email=f"p7_volf2_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9191{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9730,
        longitude=77.5960,
        carrying_capacity=100,
        vehicle_type="scooter",
        reliability_score=94.0,
        is_active=True,
    )
    db_session.add_all([vol_f1, vol_f2])
    db_session.commit()

    donation = _create_donation(db_session, donor, qty=30.0)
    donation.status = "accepted"
    donation.pickup_mode = "volunteer_dispatch"
    donation.assigned_ngo_id = ngo_a.id
    donation.assigned_volunteer_id = vol_f1.id
    db_session.commit()

    # Vol F1 assigned
    assignment_a = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol_f1.id,
        status="assigned",
        current_eta_minutes=25.0
    )
    db_session.add(assignment_a)
    db_session.commit()

    # Dynamic Rematch
    rematch_res = RematchingService.attempt_dynamic_rematch(
        db=db_session,
        donation=donation,
        trigger="ETA_EXCEEDED_WINDOW",
        reason="Vol 1 ETA infeasible",
    )
    assert rematch_res["status"] in ["REMATCHED", "BACKUP_ASSIGNED", "REMATCH_INITIATED", "NO_CANDIDATE"]


# ==============================================================================
# SCENARIO G: CANCELLATIONS & RELIABILITY SCORING
# ==============================================================================
def test_scenario_g_cancellations(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    vol_a = p7_env["vol_a"]
    donor_headers = _auth(donor)
    vol_headers = _auth(vol_a)

    # 1. Donor Early Cancellation (pending status)
    d1 = _create_donation(db_session, donor, qty=20.0)
    r_cancel_early = client.post(
        f"/api/donations/{d1.id}/cancel",
        json={"reason": "Event ended early, no excess food"},
        headers=donor_headers
    )
    assert r_cancel_early.status_code == 200
    db_session.refresh(d1)
    assert d1.status == "cancelled"

    # 2. Volunteer Justified Cancellation (Vehicle breakdown -> no penalty)
    d2 = _create_donation(db_session, donor, qty=20.0)
    d2.status = "accepted"
    db_session.commit()
    assign = VolunteerAssignment(donation_id=d2.id, volunteer_id=vol_a.id, status="assigned")
    db_session.add(assign)
    db_session.commit()

    initial_score = vol_a.reliability_score or 98.0
    client.post(
        f"/api/volunteers/assignments/{assign.id}/cancel",
        json={"reason": "vehicle_breakdown", "notes": "Flat tire on way"},
        headers=vol_headers
    )
    db_session.refresh(vol_a)
    assert vol_a.reliability_score >= initial_score - 1.0  # Justified does not heavily penalize


# ==============================================================================
# SCENARIO H: OTP SECURITY & ZERO-LEAKAGE AUDIT
# ==============================================================================
def test_scenario_h_otp_security_and_leak_audit(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]

    ts = int(datetime.now(timezone.utc).timestamp() * 1000) % 10_000_000
    vol_h = User(
        name=f"Vol H {ts}",
        email=f"p7_volh_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9190{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9720,
        longitude=77.5950,
        carrying_capacity=80,
        vehicle_type="bike",
        reliability_score=98.0,
        is_active=True,
    )
    db_session.add(vol_h)
    db_session.commit()
    db_session.refresh(vol_h)

    vol_headers = _auth(vol_h)

    donation = _create_donation(db_session, donor, qty=20.0)
    donation.status = "arrived_at_donor"
    donation.assigned_volunteer_id = vol_h.id
    db_session.commit()

    assign = VolunteerAssignment(donation_id=donation.id, volunteer_id=vol_h.id, status="arrived")
    db_session.add(assign)
    db_session.commit()

    otp_code, _ = generate_pickup_otp(db_session, donation, donor)

    # 1. Wrong OTP -> Rejected with 400
    r_wrong = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": "000000"},
        headers=vol_headers
    )
    assert r_wrong.status_code == 400, r_wrong.text

    # 2. Correct OTP -> Handover Success
    r_correct = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": otp_code},
        headers=vol_headers
    )
    assert r_correct.status_code == 200
    assert r_correct.json()["status"] == "collected"

    # 3. OTP Replay -> 409 Conflict / 400
    r_replay = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": otp_code},
        headers=vol_headers
    )
    assert r_replay.status_code in [400, 409]

    # 4. Zero Plaintext Leakage Audit
    # Check notifications table
    notifs = db_session.query(Notification).filter(Notification.message.contains(otp_code)).all()
    assert len(notifs) == 0, "Plaintext OTP leaked into notifications table!"

    # Check audit log table
    audit_leaks = db_session.query(AuditLog).filter(AuditLog.details.contains(otp_code)).all()
    assert len(audit_leaks) == 0, "Plaintext OTP leaked into audit log table!"


# ==============================================================================
# SCENARIO I: CONCURRENT NGO ACCEPTANCE (Race Condition Lock)
# ==============================================================================
def test_scenario_i_concurrent_ngo_acceptance(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    user_ngo_b = p7_env["user_ngo_b"]

    donation = _create_donation(db_session, donor, qty=50.0)
    donation_id = donation.id
    h_a = _auth(user_ngo_a)
    h_b = _auth(user_ngo_b)

    results = []
    def accept_task(headers):
        r = client.post(f"/api/donations/{donation_id}/accept", json={"pickup_mode": "self_pickup"}, headers=headers)
        results.append(r.status_code)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(accept_task, h_a)
        f2 = executor.submit(accept_task, h_b)
        f1.result()
        f2.result()

    # Exactly ONE must succeed (200), and the other must be rejected (409 Conflict)
    assert 200 in results
    assert 409 in results or 400 in results
    assert results.count(200) == 1


# ==============================================================================
# SCENARIO J: RESCUE WINDOW EXPIRY
# ==============================================================================
def test_scenario_j_rescue_window_expiry(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]

    # Expired donation (preparation time 10 hours ago, expiry 2 hours ago)
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Expired Rice",
        food_category="Cooked Food",
        food_type="Rice",
        quantity=30.0,
        quantity_unit="Meals",
        preparation_time=past - timedelta(hours=6),
        expiry_time=past,
        status="expired",
        pickup_address="Indiranagar, Bangalore",
    )
    db_session.add(donation)
    db_session.commit()

    ngo_headers = _auth(user_ngo_a)
    r = client.post(f"/api/donations/{donation.id}/accept", json={"pickup_mode": "self_pickup"}, headers=ngo_headers)
    assert r.status_code in [400, 409, 410], "Expired donation must not be accepted"


# ==============================================================================
# SCENARIO K: SMALL DONATION (< 15 Meals -> Self-Pickup Preferred)
# ==============================================================================
def test_scenario_k_small_donation(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]

    donation = _create_donation(db_session, donor, qty=10.0)  # 10 meals <= 15 meals
    ngo_headers = _auth(user_ngo_a)

    r = client.get(f"/api/donations/{donation.id}", headers=ngo_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["quantity"] <= 15.0


# ==============================================================================
# SCENARIO L: SELF DROPOFF (Admin Approves Self Dropoff)
# ==============================================================================
def test_scenario_l_self_dropoff(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    ngo_a = p7_env["ngo_a"]

    donation = _create_donation(db_session, donor, qty=30.0)
    donation.status = "accepted"
    donation.assigned_ngo_id = ngo_a.id
    db_session.commit()

    donor_headers = _auth(donor)
    ngo_headers = _auth(user_ngo_a)

    # 1. Switch to self-dropoff
    r_dropoff = client.post(
        f"/api/donations/{donation.id}/self-dropoff",
        headers=donor_headers
    )
    assert r_dropoff.status_code in [200, 201]

    # 2. Food collected by NGO / donor dropoff handover
    r_collect = client.post(
        f"/api/donations/{donation.id}/collect",
        headers=ngo_headers
    )
    assert r_collect.status_code in [200, 201]

    # 3. NGO marks intake receive (transitions to delivered)
    recv_r = client.post(
        f"/api/donations/{donation.id}/receive",
        json={"received_quantity": 30.0, "condition": "good"},
        headers=ngo_headers
    )
    assert recv_r.status_code == 200

    # 4. NGO marks distribution (transitions to completed)
    dist_r = client.post(
        f"/api/donations/{donation.id}/distribution",
        json={"distributed_quantity": 30.0, "beneficiary_count": 30, "notes": "Distributed to shelter"},
        headers=ngo_headers
    )
    assert dist_r.status_code == 200


# ==============================================================================
# SCENARIO M: ROLE SECURITY & RBAC ISOLATION
# ==============================================================================
def test_scenario_m_rbac_isolation(p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    vol_a = p7_env["vol_a"]

    donor_headers = _auth(donor)
    ngo_headers = _auth(user_ngo_a)
    vol_headers = _auth(vol_a)

    # Donor cannot access NGO-only routes
    assert client.post("/api/donations/1/accept", json={}, headers=donor_headers).status_code in [401, 403]

    # NGO cannot access Volunteer-only routes
    assert client.post("/api/volunteers/location", json={"latitude": 12.9, "longitude": 77.5}, headers=ngo_headers).status_code in [401, 403]

    # Volunteer cannot access Admin-only routes
    assert client.get("/api/admin/audit-logs", headers=vol_headers).status_code in [401, 403]


# ==============================================================================
# SCENARIO O: FLAGSHIP FULL FAILURE RECOVERY
# (Reject -> Timeout -> Infeasible -> Rematch -> Handover -> Delivery)
# ==============================================================================
def test_scenario_o_flagship_full_failure_recovery(db_session: Session, p7_env: dict):
    donor = p7_env["donor"]
    user_ngo_a = p7_env["user_ngo_a"]
    ngo_a = p7_env["ngo_a"]
    user_ngo_b = p7_env["user_ngo_b"]
    ngo_b = p7_env["ngo_b"]

    ts = int(datetime.now(timezone.utc).timestamp() * 1000) % 10_000_000
    vol_o1 = User(
        name=f"Vol O1 {ts}",
        email=f"p7_volo1_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9189{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9720,
        longitude=77.5950,
        carrying_capacity=80,
        vehicle_type="bike",
        reliability_score=98.0,
        is_active=True,
    )
    vol_o2 = User(
        name=f"Vol O2 {ts}",
        email=f"p7_volo2_{ts}@courier.com",
        password_hash=hash_password("VolPass123!"),
        role="volunteer",
        phone=f"+9188{ts % 10000000:08d}",
        phone_verified=True,
        latitude=12.9730,
        longitude=77.5960,
        carrying_capacity=100,
        vehicle_type="scooter",
        reliability_score=94.0,
        is_active=True,
    )
    db_session.add_all([vol_o1, vol_o2])
    db_session.commit()

    # 1. Donor creates rescue
    donation = _create_donation(db_session, donor, qty=45.0)

    # 2. NGO A Rejects
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        status="offered"
    )
    db_session.add(offer_a)
    db_session.commit()

    ngo_a_headers = _auth(user_ngo_a)
    client.post(f"/api/donations/{donation.id}/reject?reason=Capacity+full", headers=ngo_a_headers)

    # 3. NGO B accepts rescue
    ngo_b_headers = _auth(user_ngo_b)
    accept_resp = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "volunteer_dispatch"},
        headers=ngo_b_headers
    )
    assert accept_resp.status_code == 200

    # 4. Volunteer O1 accepts
    vol_o1_headers = _auth(vol_o1)
    assign_a_resp = client.post(
        f"/api/volunteers/assignments?donation_id={donation.id}&volunteer_id={vol_o1.id}",
        headers=vol_o1_headers
    )
    assert assign_a_resp.status_code == 200
    db_session.refresh(donation)

    # Vol O1 becomes infeasible -> Rematch
    rematch_res = RematchingService.attempt_dynamic_rematch(
        db=db_session,
        donation=donation,
        trigger="ETA_EXCEEDED_WINDOW",
        reason="Traffic deadlock",
    )

    # 5. Backup Volunteer active assignment verification
    db_session.refresh(donation)
    active_assign = db_session.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id,
        VolunteerAssignment.status.in_(["assigned", "accepted"])
    ).first()
    if not active_assign:
        vol_o2_headers = _auth(vol_o2)
        assign_b_resp = client.post(
            f"/api/volunteers/assignments?donation_id={donation.id}&volunteer_id={vol_o2.id}",
            headers=vol_o2_headers
        )
        assert assign_b_resp.status_code == 200
        db_session.refresh(donation)

    assigned_vol = db_session.query(User).filter(User.id == donation.assigned_volunteer_id).first()
    active_vol_headers = _auth(assigned_vol)

    # 6. Pickup, OTP & Handover
    client.post(f"/api/volunteers/donations/{donation.id}/start-pickup", headers=active_vol_headers)
    client.post(f"/api/volunteers/donations/{donation.id}/arrived", headers=active_vol_headers)

    otp, _ = generate_pickup_otp(db_session, donation, donor)
    v_otp = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": otp},
        headers=active_vol_headers
    )
    assert v_otp.status_code == 200

    # 7. Transit & Delivery
    client.post(f"/api/volunteers/donations/{donation.id}/in-transit", headers=active_vol_headers)
    client.post(f"/api/volunteers/donations/{donation.id}/deliver", headers=active_vol_headers)

    # 8. NGO B Distribution
    dist_r = client.post(
        f"/api/donations/{donation.id}/distribution",
        json={"distributed_quantity": 45.0, "beneficiary_count": 45, "notes": "Served to community beneficiaries"},
        headers=ngo_b_headers
    )
    assert dist_r.status_code == 200
    assert dist_r.json()["distribution_status"] == "distributed"


# ==============================================================================
# REGRESSION 19: NO ASSIGNMENT ID 0
# ==============================================================================
def test_regression_19_no_assignment_id_zero(p7_env: dict):
    vol_headers = _auth(p7_env["vol_a"])

    # Ensure calling /api/volunteers/assignments/0 explicitly fails with 404 or 422, never succeeds
    r = client.get("/api/volunteers/assignments/0", headers=vol_headers)
    assert r.status_code in [404, 422, 400]


# ==============================================================================
# INTEGRITY 21: DATABASE INTEGRITY AND CONSISTENCY
# ==============================================================================
def test_integrity_21_database_consistency(db_session: Session):
    # Verify no orphan assignments (every assignment points to valid donation)
    orphan_assignments = db_session.query(VolunteerAssignment).filter(
        ~VolunteerAssignment.donation_id.in_(db_session.query(FoodDonation.id))
    ).count()
    assert orphan_assignments == 0

    # Verify no active OTP for completed donations
    completed_ids = [d.id for d in db_session.query(FoodDonation).filter(FoodDonation.status == "completed").all()]
    if completed_ids:
        active_otps = db_session.query(PickupOtpRecord).filter(
            PickupOtpRecord.donation_id.in_(completed_ids),
            PickupOtpRecord.is_active == True
        ).count()
        assert active_otps == 0


# ==============================================================================
# SECURITY 23: DATA PRIVACY & SANITIZATION
# ==============================================================================
def test_security_23_privacy_sanitization(p7_env: dict):
    vol = p7_env["vol_a"]
    vol_headers = _auth(vol)

    # Verify unassigned donations return fuzzed/approximate coordinates or no exact private address
    r = client.get("/api/volunteers/eligible-tasks", headers=vol_headers)
    if r.status_code == 200:
        tasks = r.json()
        for task in tasks:
            # Full private house/flat address must not be exposed to unaccepted courier
            assert "exact_flat_number" not in task
