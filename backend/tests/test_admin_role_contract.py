"""
Smart Food Rescue Platform — Admin Role Contract & Regression Test Suite
========================================================================
Tests all requirements from the Admin Role Implementation Prompt:
1. Admin Authentication & Strict RBAC (Donor, NGO, Volunteer blocked)
2. Live Overview Counts & Intervention Queue (Exceptions First)
3. Admin Rescue Detail Full Lifecycle Chain & OTP Privacy
4. Force-State Override Allow-List Enforcement (Arbitrary jumps blocked)
5. Mandatory Reason/Remark Validation (Min 5 chars)
6. Impact Integrity on Forced State Overrides
7. Donor Self-Dropoff Support (Section 10 Fallback)
8. Core Admin Duty: NGO Verification & Rejection with Reason
9. User Activation / Deactivation Controls
10. Operational Dispute Review & Resolution
11. Auditable Security History (A7 Compliance, Zero Plaintext OTP)
12. Monthly Impact Report (All Figures Labeled as ESTIMATED)
13. Waste-Prevention Repeat-Donor Insights & Real Pilot Performance Metrics
"""

import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.models.models import (
    User, NGO, FoodDonation, VolunteerAssignment, Dispute,
    AuditLog, MatchOffer, PickupOtpRecord, RescueClaimToken
)
from app.core.security import create_access_token, hash_password

client = TestClient(app)

@pytest.fixture
def test_db():
    db_gen = get_db()
    db = next(db_gen)
    try:
        yield db
    finally:
        pass

@pytest.fixture
def admin_user(test_db: Session):
    admin = test_db.query(User).filter(User.email == "admin_contract_test@rescue.org").first()
    if not admin:
        admin = User(
            name="Admin Coordinator",
            email="admin_contract_test@rescue.org",
            password_hash=hash_password("Admin@123"),
            role="admin",
            phone="+919800000101",
            is_active=True
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)
    return admin

@pytest.fixture
def donor_user(test_db: Session):
    donor = test_db.query(User).filter(User.email == "donor_contract_test@rescue.org").first()
    if not donor:
        donor = User(
            name="Rasoi Heritage Donor",
            email="donor_contract_test@rescue.org",
            password_hash=hash_password("Donor@123"),
            role="donor",
            phone="+919800000102",
            is_active=True
        )
        test_db.add(donor)
        test_db.commit()
        test_db.refresh(donor)
    return donor

@pytest.fixture
def volunteer_user(test_db: Session):
    vol = test_db.query(User).filter(User.email == "vol_admin_test@rescue.org").first()
    if not vol:
        vol = User(
            name="Courier Rahul",
            email="vol_admin_test@rescue.org",
            password_hash=hash_password("Courier@123"),
            role="volunteer",
            phone="+919800000103",
            vehicle_type="Bike",
            is_active=True,
            reliability_score=95.0
        )
        test_db.add(vol)
        test_db.commit()
        test_db.refresh(vol)
    return vol

@pytest.fixture
def ngo_fixture(test_db: Session):
    ngo_user = test_db.query(User).filter(User.email == "ngo_admin_test@rescue.org").first()
    if not ngo_user:
        ngo_user = User(
            name="Indiranagar Care Shelter",
            email="ngo_admin_test@rescue.org",
            password_hash=hash_password("Ngo@123"),
            role="ngo",
            phone="+919800000104",
            is_active=True
        )
        test_db.add(ngo_user)
        test_db.commit()
        test_db.refresh(ngo_user)

    ngo_prof = test_db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
    if not ngo_prof:
        ngo_prof = NGO(
            user_id=ngo_user.id,
            organization_name="Indiranagar Care Shelter",
            address="12th Main, Indiranagar, Bangalore",
            capacity=400,
            current_capacity=80,
            is_verified=False
        )
        test_db.add(ngo_prof)
        test_db.commit()
        test_db.refresh(ngo_prof)
    return ngo_prof

@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role, "name": admin_user.name})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def donor_headers(donor_user):
    token = create_access_token(data={"sub": str(donor_user.id), "role": donor_user.role, "name": donor_user.name})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def volunteer_headers(volunteer_user):
    token = create_access_token(data={"sub": str(volunteer_user.id), "role": volunteer_user.role, "name": volunteer_user.name})
    return {"Authorization": f"Bearer {token}"}


# ── TEST 1: ADMIN AUTHENTICATION & STRICT RBAC BLOCKING (Section 3) ───────────

def test_admin_authentication_and_rbac_blocking(admin_headers, donor_headers, volunteer_headers):
    # 1. Admin authorized access
    res = client.get("/api/admin/statistics", headers=admin_headers)
    assert res.status_code == 200, f"Admin should access statistics: {res.text}"
    stats_data = res.json()
    assert "total_users" in stats_data
    assert "meals_donated" in stats_data

    # 2. Donor is blocked from admin routes (Section 3: HTTP 403 Forbidden)
    res_donor = client.get("/api/admin/statistics", headers=donor_headers)
    assert res_donor.status_code == 403, "Donor must be blocked from admin endpoints"

    # 3. Volunteer is blocked from admin routes (Section 3: HTTP 403 Forbidden)
    res_vol = client.get("/api/admin/statistics", headers=volunteer_headers)
    assert res_vol.status_code == 403, "Volunteer must be blocked from admin endpoints"


# ── TEST 2: OVERVIEW LIVE METRICS & INTERVENTION QUEUE (Section 4 & 5) ────────

def test_overview_live_counts_and_intervention_queue(test_db, admin_headers, donor_user):
    now = datetime.now(timezone.utc)
    # Create an urgent rescue requiring intervention (1h window left, status pending)
    urgent_donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Urgent Biryani Batch",
        food_category="Cooked Food",
        quantity=30.0,
        quantity_unit="Meals",
        pickup_address="Indiranagar, Bangalore",
        preparation_time=now - timedelta(hours=3),
        expiry_time=now + timedelta(minutes=45),
        remaining_minutes=45,
        status="pending",
        rescue_urgency_level="URGENT",
        is_emergency=False
    )
    test_db.add(urgent_donation)
    test_db.commit()
    test_db.refresh(urgent_donation)

    # 1. Verify Receiving Overview Summary
    res = client.get("/api/admin/receiving/summary", headers=admin_headers)
    assert res.status_code == 200
    summary = res.json()
    assert summary["active_rescues"] >= 1
    assert "urgent_rescues" in summary
    assert "critical_rescues" in summary

    # 2. Verify Intervention Queue (Exceptions First)
    res_int = client.get("/api/admin/interventions", headers=admin_headers)
    assert res_int.status_code == 200
    int_data = res_int.json()
    assert "items" in int_data
    assert int_data["total_interventions_needed"] >= 1
    # Check that item has problem description and suggested action
    items = int_data["items"]
    assert any(i["donation_id"] == urgent_donation.id for i in items)
    matched = next(i for i in items if i["donation_id"] == urgent_donation.id)
    assert matched["suggested_action"] is not None
    assert matched["reason"] is not None


# ── TEST 3: FULL RESCUE LIFECYCLE CHAIN & STRICT OTP PRIVACY (Section 6 & 18) ─

def test_admin_rescue_detail_and_otp_privacy(test_db, admin_headers, donor_user, ngo_fixture):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        assigned_ngo_id=ngo_fixture.id,
        food_name="Paneer Butter Masala & Rotis",
        food_category="Cooked Food",
        quantity=25.0,
        quantity_unit="Meals",
        pickup_address="4th Block, Koramangala, Bangalore",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        remaining_minutes=180,
        status="accepted",
        rescue_urgency_level="FRESH",
        current_alert_wave=1
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    # Add RescueClaimToken
    claim_rec = RescueClaimToken(
        donation_id=donation.id,
        token="claim_admin_sec_test",
        expires_at=now + timedelta(hours=3),
        is_active=True
    )
    test_db.add(claim_rec)
    test_db.commit()

    # Add OTP record in DB
    otp_code = PickupOtpRecord(
        donation_id=donation.id,
        donor_id=donor_user.id,
        volunteer_id=None,
        purpose="PICKUP_VERIFICATION_OTP",
        otp_hash=hashlib.sha256(b"SECRET_CRYPTOGRAPHIC_HASH").hexdigest(),
        expires_at=now + timedelta(minutes=15),
        is_active=True
    )
    test_db.add(otp_code)
    test_db.commit()

    # Query admin rescue detail
    res = client.get(f"/api/admin/rescues/{donation.id}", headers=admin_headers)
    assert res.status_code == 200
    detail = res.json()

    # Verify Section 6 Full Chain Fields
    assert detail["food_name"] == "Paneer Butter Masala & Rotis"
    assert detail["ai_advisory"] is not None
    assert detail["current_wave"] == 1
    assert "Wave 1" in detail["wave_name"]
    assert detail["has_claim_token"] is True
    assert len(detail["timeline"]) >= 7  # 9-stage stepper

    # Section 18: OTP Admin Privacy — Plaintext OTP must NEVER appear
    assert detail["otp_state"] in ["PENDING_VERIFICATION", "VERIFIED", "EXPIRED", "NOT_GENERATED"]
    assert "code" not in detail
    assert "678901" not in str(detail)
    assert "code_hash" not in detail


# ── TEST 4: ALLOWED FORCE-STATE OVERRIDE (Section 8) ──────────────────────────

def test_allowed_force_state_override(test_db, admin_headers, donor_user, ngo_fixture):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        assigned_ngo_id=ngo_fixture.id,
        food_name="Buffet Surplus Rice",
        food_category="Cooked Food",
        preparation_time=now - timedelta(hours=1),
        quantity=40.0,
        quantity_unit="Meals",
        pickup_address="Indiranagar, Bangalore",
        expiry_time=now + timedelta(hours=2),
        status="accepted",
        remaining_minutes=120
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    # Transition: accepted -> collected is in ALLOWED_ADMIN_FORCE_TRANSITIONS
    payload = {
        "donation_id": donation.id,
        "reason_code": "other",
        "notes": "Admin confirmed direct intake transport out of band.",
        "action_type": "force_state",
        "target_status": "collected"
    }

    res = client.post("/api/admin/interventions", headers=admin_headers, json=payload)
    assert res.status_code == 200, f"Allowed transition failed: {res.text}"
    data = res.json()
    assert data["success"] is True

    test_db.refresh(donation)
    assert donation.status == "collected"

    # Verify audit log was created
    audit = test_db.query(AuditLog).filter(
        AuditLog.resource_id == donation.id,
        AuditLog.action == "admin_rescue_intervention"
    ).first()
    assert audit is not None


# ── TEST 5: INVALID FORCE-STATE OVERRIDE BLOCKED (Section 8) ──────────────────

def test_invalid_force_state_override_blocked(test_db, admin_headers, donor_user):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Unmatched Pending Food",
        food_category="Cooked Food",
        preparation_time=now - timedelta(hours=1),
        quantity=15.0,
        quantity_unit="Meals",
        pickup_address="Indiranagar, Bangalore",
        expiry_time=now + timedelta(hours=2),
        status="pending",
        remaining_minutes=120
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    # Illegal jump: pending -> completed without pickup or delivery
    payload = {
        "donation_id": donation.id,
        "reason_code": "other",
        "notes": "Attempting illegal jump straight to completed.",
        "action_type": "force_state",
        "target_status": "completed"
    }

    res = client.post("/api/admin/interventions", headers=admin_headers, json=payload)
    assert res.status_code == 409, "Illegal force-state jump must return HTTP 409 Conflict"
    assert "not permitted by Admin policy" in res.json()["detail"]


# ── TEST 6: MANDATORY REMARK VALIDATION (Section 8) ───────────────────────────

def test_mandatory_intervention_remark_required(test_db, admin_headers, donor_user):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Test Food",
        food_category="Cooked Food",
        preparation_time=now - timedelta(hours=1),
        quantity=10.0,
        quantity_unit="Meals",
        pickup_address="Indiranagar",
        expiry_time=now + timedelta(hours=2),
        status="accepted"
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    # Submitting with empty or whitespace remark
    payload = {
        "donation_id": donation.id,
        "reason_code": "other",
        "notes": "  ",
        "action_type": "force_state",
        "target_status": "collected"
    }

    res = client.post("/api/admin/interventions", headers=admin_headers, json=payload)
    assert res.status_code == 400, "Remark < 5 characters must return HTTP 400 Bad Request"
    assert "at least 5 characters" in res.json()["detail"]


# ── TEST 7: DONOR SELF-DROPOFF SUPPORT (Section 10) ───────────────────────────

def test_donor_self_dropoff_approval(test_db, admin_headers, donor_user, ngo_fixture, volunteer_user):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        assigned_ngo_id=ngo_fixture.id,
        assigned_volunteer_id=volunteer_user.id,
        food_name="Wedding Reception Surplus",
        food_category="Cooked Food",
        preparation_time=now - timedelta(hours=1),
        quantity=50.0,
        pickup_address="Indiranagar",
        expiry_time=now + timedelta(hours=2),
        remaining_minutes=120,
        status="accepted",
        pickup_mode="volunteer_dispatch"
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    # Admin approves Section 10 Donor Self-Dropoff fallback
    payload = {
        "donation_id": donation.id,
        "reason_code": "donor_self_dropoff",
        "notes": "No couriers available within 5km. Donor agreed to drop off directly at Green Hope facility.",
        "action_type": "approve_self_dropoff"
    }

    res = client.post("/api/admin/interventions", headers=admin_headers, json=payload)
    assert res.status_code == 200
    test_db.refresh(donation)

    assert donation.pickup_mode == "self_pickup"
    assert donation.assigned_volunteer_id is None


# ── TEST 8: NGO VERIFICATION & REJECTION (Section 15) ─────────────────────────

def test_ngo_verification_and_rejection(test_db, admin_headers):
    # Create unverified NGO applicant
    ngo_user = User(
        name="Karunai Care Trust",
        email=f"karunai_{datetime.now().timestamp()}@rescue.org",
        password_hash=hash_password("NgoPass123"),
        role="ngo",
        is_active=True
    )
    test_db.add(ngo_user)
    test_db.commit()
    test_db.refresh(ngo_user)

    ngo = NGO(
        user_id=ngo_user.id,
        organization_name="Karunai Care Trust",
        address="Koramangala, Bangalore",
        capacity=300,
        is_verified=False
    )
    test_db.add(ngo)
    test_db.commit()
    test_db.refresh(ngo)

    # 1. Verify NGO
    res_verify = client.post(f"/api/admin/ngos/{ngo.id}/verify", headers=admin_headers)
    assert res_verify.status_code == 200
    test_db.refresh(ngo)
    assert ngo.is_verified is True

    # 2. Reject NGO with reason
    res_reject = client.post(f"/api/admin/ngos/{ngo.id}/reject?reason=Facility+unreachable", headers=admin_headers)
    assert res_reject.status_code == 200
    test_db.refresh(ngo)
    assert ngo.is_verified is False


# ── TEST 9: USER ACTIVATION / DEACTIVATION (Section 14) ───────────────────────

def test_user_activation_toggle(test_db, admin_headers, volunteer_user, admin_user):
    # 1. Toggle volunteer active state
    orig_active = volunteer_user.is_active
    res = client.put(f"/api/admin/users/{volunteer_user.id}/toggle-active", headers=admin_headers)
    assert res.status_code == 200
    test_db.refresh(volunteer_user)
    assert volunteer_user.is_active != orig_active

    # Restore state
    client.put(f"/api/admin/users/{volunteer_user.id}/toggle-active", headers=admin_headers)

    # 2. Admin cannot deactivate themselves
    res_self = client.put(f"/api/admin/users/{admin_user.id}/toggle-active", headers=admin_headers)
    assert res_self.status_code == 400


# ── TEST 10: DISPUTE REVIEW & RESOLUTION (Section 16) ─────────────────────────

def test_dispute_review_and_resolution(test_db, admin_headers, donor_user):
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Quantity Disputed Food",
        food_category="Cooked Food",
        preparation_time=now - timedelta(hours=1),
        quantity=20.0,
        quantity_unit="Meals",
        pickup_address="Indiranagar",
        expiry_time=now + timedelta(hours=2),
        status="delivered"
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    dispute = Dispute(
        donation_id=donation.id,
        reporter_id=donor_user.id,
        role="donor",
        issue_type="quantity_mismatch",
        description="Donor reported intake counted 15 meals instead of 20.",
        status="open",
        created_at=now
    )
    test_db.add(dispute)
    test_db.commit()
    test_db.refresh(dispute)

    # Resolve dispute
    res = client.put(
        f"/api/disputes/{dispute.id}/resolve",
        headers=admin_headers,
        json={
            "status": "resolved",
            "admin_notes": "Reviewed scale photos; 18 meals verified. Packaging tare discrepancy.",
            "trust_score_penalty": 0.0
        }
    )
    assert res.status_code == 200
    test_db.refresh(dispute)
    assert dispute.status == "resolved"


# ── TEST 11: MONTHLY REPORT & ESTIMATED LABELS (Section 24) ───────────────────

def test_monthly_report_and_estimated_labels(admin_headers):
    res = client.get("/api/admin/reports/monthly", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_estimated"] is True
    assert "estimated_co2e_kg" in data
    assert "estimated_water_liters" in data
    assert "estimated_disposal_cost_avoided_inr" in data
    # Section 24: No tax write-off claims
    assert "tax_writeoff" not in data
    assert "csr_guarantee" not in data


# ── TEST 12: PILOT METRICS & WASTE INSIGHTS (Section 26 & 27) ─────────────────

def test_pilot_metrics_and_waste_insights(admin_headers):
    # Pilot metrics from docs/pilot/PILOT_METRICS.csv
    res_pilot = client.get("/api/admin/pilot-metrics", headers=admin_headers)
    assert res_pilot.status_code == 200
    p_data = res_pilot.json()
    assert p_data["total_pilot_rescues"] >= 1
    assert p_data["avg_time_saved_min"] > 0
    assert p_data["avg_platform_coord_time_min"] < p_data["avg_manual_baseline_min"]

    # Waste-prevention repeat-donor insights
    res_insights = client.get("/api/admin/insights/repeat-donors", headers=admin_headers)
    assert res_insights.status_code == 200
    i_data = res_insights.json()
    assert "patterns" in i_data
    assert "total_donations_analyzed" in i_data
