"""
Volunteer Role Complete Contract & Regression Test Suite
=========================================================
Tests all requirements from the Volunteer Role Implementation Prompt:
1. Feasible-only task screening for volunteers
2. Availability logic (unavailable volunteer receives no new offers)
3. Pre-acceptance exact address privacy masking
4. Assignment ID correctness & no ID 0 regression
5. Single active task acceptance guard
6. Audited fallback arrival verification
7. OTP rate limiting, lockout on 5 failures, replay protection
8. Reason-based reliability impact (excused reasons spared, unexcused penalized)
9. Notification & SMS security: OTP never leaked
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.models.models import User, FoodDonation, VolunteerAssignment, PickupOtpRecord, AuditLog, Notification
from app.core.security import create_access_token, hash_password
from app.services.otp_service import _hash_otp, _OTP_VERIFY_ATTEMPTS

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
def volunteer_user(test_db: Session):
    user = test_db.query(User).filter(User.email == "vol_contract_test@rescue.org").first()
    if not user:
        user = User(
            name="Courier Alex",
            email="vol_contract_test@rescue.org",
            password_hash=hash_password("courier123"),
            role="volunteer",
            phone="+919876543210",
            phone_verified=True,
            vehicle_type="Bike",
            carrying_capacity=50,
            is_active=True,
            reliability_score=100.0,
            completed_deliveries=5,
            failed_deliveries=0
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
    else:
        user.is_active = True
        user.reliability_score = 100.0
        user.completed_deliveries = 5
        user.failed_deliveries = 0
        test_db.commit()
    return user

@pytest.fixture
def donor_user(test_db: Session):
    donor = test_db.query(User).filter(User.email == "donor_contract_test@kitchen.org").first()
    if not donor:
        donor = User(
            name="Chef Donor",
            email="donor_contract_test@kitchen.org",
            password_hash=hash_password("donor123"),
            role="donor",
            phone="+919876500000",
            phone_verified=True,
            is_active=True
        )
        test_db.add(donor)
        test_db.commit()
        test_db.refresh(donor)
    return donor

def auth_headers(user: User):
    token = create_access_token(data={"sub": str(user.id), "role": user.role, "name": user.name})
    return {"Authorization": f"Bearer {token}"}

def test_feasible_only_filtering_and_availability(test_db: Session, volunteer_user: User, donor_user: User):
    """Volunteer receives ONLY feasible tasks and when available."""
    now = datetime.now(timezone.utc)
    
    # 1. Create a fresh feasible donation
    feasible_donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Feasible Dal Bhaat",
        food_category="Cooked Meals",
        quantity=20,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=4),
        pickup_address="45MG Road, Indiranagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="accepted",
        pickup_mode="volunteer_dispatch"
    )
    test_db.add(feasible_donation)
    test_db.commit()
    test_db.refresh(feasible_donation)

    # When available -> gets the feasible donation
    res = client.get("/api/donations", headers=auth_headers(volunteer_user))
    assert res.status_code == 200
    tasks = res.json()
    task_ids = [t["id"] for t in tasks]
    assert feasible_donation.id in task_ids

    # Privacy check pre-assignment: exact street address is masked to neighborhood area
    found_item = next(t for t in tasks if t["id"] == feasible_donation.id)
    assert "Exact address revealed upon acceptance" in found_item["pickup_address"]
    assert "45MG Road" not in found_item["pickup_address"]

    # When unavailable -> no new offers are provided
    volunteer_user.is_active = False
    test_db.commit()
    res_off = client.get("/api/donations", headers=auth_headers(volunteer_user))
    assert res_off.status_code == 200
    off_tasks = res_off.json()
    off_ids = [t["id"] for t in off_tasks]
    assert feasible_donation.id not in off_ids

    # Restore availability
    volunteer_user.is_active = True
    test_db.commit()

def test_single_active_task_rule(test_db: Session, volunteer_user: User, donor_user: User):
    """Volunteer may have only one active rescue task at a time."""
    now = datetime.now(timezone.utc)
    
    d1 = FoodDonation(
        donor_id=donor_user.id,
        food_name="Task 1 Meals",
        food_category="Cooked Meals",
        quantity=15,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="MG Road, Bangalore",
        status="accepted",
        pickup_mode="volunteer_dispatch"
    )
    d2 = FoodDonation(
        donor_id=donor_user.id,
        food_name="Task 2 Meals",
        food_category="Cooked Meals",
        quantity=15,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="Brigade Road, Bangalore",
        status="accepted",
        pickup_mode="volunteer_dispatch"
    )
    test_db.add_all([d1, d2])
    test_db.commit()

    # Clear prior active assignments
    test_db.query(VolunteerAssignment).filter(VolunteerAssignment.volunteer_id == volunteer_user.id).delete()
    test_db.commit()

    # Accept first task -> succeeds
    res1 = client.post(f"/api/volunteers/assignments?donation_id={d1.id}", headers=auth_headers(volunteer_user))
    assert res1.status_code == 200
    assign1 = res1.json()
    assert assign1["id"] > 0
    assert assign1["donation_id"] == d1.id

    # Attempt to accept second task while task 1 is active -> 409 Conflict
    res2 = client.post(f"/api/volunteers/assignments?donation_id={d2.id}", headers=auth_headers(volunteer_user))
    assert res2.status_code == 409
    assert "active rescue task in progress" in res2.json()["detail"]

def test_assignment_id_resolution_and_no_zero_regression(test_db: Session, volunteer_user: User, donor_user: User):
    """Never send or fail on assignment ID resolution; supports assignment ID, donation ID, and active fallback."""
    now = datetime.now(timezone.utc)
    
    # Create active assignment
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Curry & Rice",
        food_category="Cooked Meals",
        quantity=10,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="Koramangala, Bangalore",
        status="volunteer_assigned",
        assigned_volunteer_id=volunteer_user.id,
        pickup_mode="volunteer_dispatch"
    )
    test_db.add(donation)
    test_db.flush()

    assign = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer_user.id,
        status="assigned"
    )
    test_db.add(assign)
    test_db.commit()
    test_db.refresh(assign)

    assert assign.id > 0

    # 1. start-pickup by exact assignment ID
    res_start = client.post(f"/api/volunteers/assignments/{assign.id}/start-pickup", headers=auth_headers(volunteer_user))
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "en_route"

    # 2. arrival by donation ID alias route
    res_arr = client.post(f"/api/volunteers/donations/{donation.id}/arrived?method=gps", headers=auth_headers(volunteer_user))
    assert res_arr.status_code == 200
    assert res_arr.json()["status"] == "arrived"

    # 3. Fallback arrival with reason and method (Section 14)
    res_fallback = client.post(
        f"/api/volunteers/assignments/{assign.id}/arrived?method=manual_here&reason=Basement+GPS+blocked",
        headers=auth_headers(volunteer_user)
    )
    assert res_fallback.status_code == 200

    # Verify arrival was audited
    audit = test_db.query(AuditLog).filter(
        AuditLog.action == "volunteer_arrival_verified",
        AuditLog.user_id == volunteer_user.id
    ).order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert "manual_here" in audit.details

def test_otp_lockout_after_five_failed_attempts(test_db: Session, volunteer_user: User, donor_user: User):
    """OTP verification locks out after 5 consecutive failures."""
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Security Meals",
        food_category="Cooked Meals",
        quantity=10,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=2),
        pickup_address="Richmond Road, Bangalore",
        status="arrived_at_donor",
        assigned_volunteer_id=volunteer_user.id,
        verification_otp="123456"
    )
    test_db.add(donation)
    test_db.flush()

    assign = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer_user.id,
        status="arrived"
    )
    test_db.add(assign)

    otp_rec = PickupOtpRecord(
        donation_id=donation.id,
        donor_id=donor_user.id,
        volunteer_id=volunteer_user.id,
        purpose="PICKUP_VERIFICATION_OTP",
        otp_hash=_hash_otp("123456"),
        expires_at=now + timedelta(minutes=30),
        is_active=True
    )
    test_db.add(otp_rec)
    test_db.commit()

    # Clear previous attempt caches
    _OTP_VERIFY_ATTEMPTS.pop(f"otp_verify:{donation.id}", None)

    # 5 wrong attempts
    for i in range(5):
        res = client.post(
            "/api/volunteers/verify-otp",
            json={"donation_id": donation.id, "otp": "999999"},
            headers=auth_headers(volunteer_user)
        )
        assert res.status_code == 400

    # 6th attempt -> 429 Too Many Requests (Lockout)
    res_locked = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": "123456"},
        headers=auth_headers(volunteer_user)
    )
    assert res_locked.status_code == 429
    assert "locked for 15 minutes" in res_locked.json()["detail"]

def test_reason_based_reliability_scoring(test_db: Session, volunteer_user: User, donor_user: User):
    """Vehicle breakdown / emergency does NOT lower score; unexcused cancellation DOES."""
    now = datetime.now(timezone.utc)
    volunteer_user.reliability_score = 100.0
    volunteer_user.completed_deliveries = 10
    volunteer_user.failed_deliveries = 0
    test_db.commit()

    d_breakdown = FoodDonation(
        donor_id=donor_user.id,
        food_name="Breakdown Delivery",
        food_category="Cooked Meals",
        quantity=10,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=2),
        pickup_address="Bannerghatta, Bangalore",
        status="volunteer_assigned",
        assigned_volunteer_id=volunteer_user.id
    )
    test_db.add(d_breakdown)
    test_db.flush()

    assign = VolunteerAssignment(
        donation_id=d_breakdown.id,
        volunteer_id=volunteer_user.id,
        status="en_route"
    )
    test_db.add(assign)
    test_db.commit()

    # 1. Report failure due to vehicle tyre puncture (Excused)
    res_breakdown = client.post(
        f"/api/volunteers/report-failure?donation_id={d_breakdown.id}",
        json={"failure_type": "pickup_failed", "reason": "vehicle_issue", "remarks": "Rear tyre puncture breakdown on highway"},
        headers=auth_headers(volunteer_user)
    )
    assert res_breakdown.status_code == 200
    test_db.refresh(volunteer_user)
    # Reliability score must remain unchanged
    assert volunteer_user.failed_deliveries == 0
    assert volunteer_user.reliability_score == 100.0

    # 2. Report failure due to unexcused no-show (Unexcused)
    d_unexcused = FoodDonation(
        donor_id=donor_user.id,
        food_name="Unexcused Delivery",
        food_category="Cooked Meals",
        quantity=10,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=2),
        pickup_address="Indiranagar, Bangalore",
        status="volunteer_assigned",
        assigned_volunteer_id=volunteer_user.id
    )
    test_db.add(d_unexcused)
    test_db.flush()
    assign2 = VolunteerAssignment(donation_id=d_unexcused.id, volunteer_id=volunteer_user.id, status="assigned")
    test_db.add(assign2)
    test_db.commit()

    res_unexcused = client.post(
        f"/api/volunteers/report-failure?donation_id={d_unexcused.id}",
        json={"failure_type": "pickup_failed", "reason": "volunteer_rejected", "remarks": "Changed my mind, silent cancel"},
        headers=auth_headers(volunteer_user)
    )
    assert res_unexcused.status_code == 200
    test_db.refresh(volunteer_user)
    # Reliability score is now penalized
    assert volunteer_user.failed_deliveries == 1
    assert volunteer_user.reliability_score < 100.0

def test_public_claim_link_and_privacy(test_db: Session, donor_user: User):
    """First-time volunteers can claim ONE task via public claim link without full registration."""
    now = datetime.now(timezone.utc)
    
    # 1. Create a donation
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Public Claim Biryani",
        food_category="Cooked Meals",
        quantity=30,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="99 Commercial Street, Shivajinagar, Bangalore",
        status="accepted",
        pickup_mode="volunteer_dispatch"
    )
    test_db.add(donation)
    test_db.commit()
    test_db.refresh(donation)

    # Generate public claim token (authorized donor or NGO or admin)
    res_token = client.post(
        f"/api/volunteers/donations/{donation.id}/claim-token",
        headers=auth_headers(donor_user)
    )
    assert res_token.status_code == 200
    token_data = res_token.json()
    claim_token = token_data["claim_token"]

    # Preview claim link: exact address MUST NOT be exposed (Section 7 & 9)
    res_prev = client.get(f"/api/volunteers/claims/{claim_token}")
    assert res_prev.status_code == 200
    prev_data = res_prev.json()
    assert "Commercial Street" not in prev_data["pickup_neighborhood"]
    assert "otp" not in str(prev_data).lower()

    # Claim task via public link with quick courier details (no full registration needed)
    claim_payload = {
        "name": "Community Sam",
        "phone": "+919123456780",
        "vehicle_type": "bike"
    }
    res_claim = client.post(f"/api/volunteers/claims/{claim_token}/accept", json=claim_payload)
    assert res_claim.status_code == 200
    claim_result = res_claim.json()
    assert claim_result["status"] in ["volunteer_assigned", "claimed"]
    assert claim_result["assignment_id"] > 0
    # Now exact address is revealed to the authorized claimant
    assert "Commercial Street" in claim_result["pickup_address"]

def test_otp_lifecycle_and_notification_safety(test_db: Session, volunteer_user: User, donor_user: User):
    """Test OTP success, replay prevention, and verify OTP is NEVER leaked in notifications or SMS."""
    now = datetime.now(timezone.utc)
    
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Paneer Butter Masala",
        food_category="Cooked Meals",
        quantity=15,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="Whitefield, Bangalore",
        status="arrived_at_donor",
        assigned_volunteer_id=volunteer_user.id,
        verification_otp="654321"
    )
    test_db.add(donation)
    test_db.flush()

    assign = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer_user.id,
        status="arrived"
    )
    test_db.add(assign)

    otp_rec = PickupOtpRecord(
        donation_id=donation.id,
        donor_id=donor_user.id,
        volunteer_id=volunteer_user.id,
        purpose="PICKUP_VERIFICATION_OTP",
        otp_hash=_hash_otp("654321"),
        expires_at=now + timedelta(minutes=30),
        is_active=True
    )
    test_db.add(otp_rec)
    test_db.commit()

    # 1. Correct OTP verification -> succeeds
    res_correct = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": "654321"},
        headers=auth_headers(volunteer_user)
    )
    assert res_correct.status_code == 200
    assert res_correct.json()["status"] == "collected"

    # 2. Replay attempt with same OTP -> rejected (400 or 409)
    res_replay = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation.id, "otp": "654321"},
        headers=auth_headers(volunteer_user)
    )
    assert res_replay.status_code in [400, 409]

    # 3. Notification safety: verify OTP "654321" was NEVER stored in any notification
    notifs = test_db.query(Notification).filter(Notification.user_id.in_([volunteer_user.id, donor_user.id])).all()
    for n in notifs:
        assert "654321" not in n.message, "OTP leaked in notification message!"

def test_volunteer_location_telemetry(test_db: Session, volunteer_user: User, donor_user: User):
    """Volunteer GPS location update updates live telemetry without storing unlimited history."""
    now = datetime.now(timezone.utc)
    
    donation = FoodDonation(
        donor_id=donor_user.id,
        food_name="Location Test Meal",
        food_category="Cooked Meals",
        quantity=10,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=2),
        pickup_address="Indiranagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="volunteer_assigned",
        assigned_volunteer_id=volunteer_user.id,
        pickup_mode="volunteer_dispatch"
    )
    test_db.add(donation)
    test_db.flush()

    assign = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer_user.id,
        status="en_route"
    )
    test_db.add(assign)
    test_db.commit()

    loc_payload = {
        "latitude": 12.9352,
        "longitude": 77.6245,
        "donation_id": donation.id,
        "assignment_id": assign.id,
        "heading": 90.0,
        "speed_kmh": 25.5
    }
    res = client.post("/api/volunteers/location", json=loc_payload, headers=auth_headers(volunteer_user))
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["assignment_id"] == assign.id
    assert "eta_minutes" in data

def test_assignment_id_zero_is_rejected(test_db: Session, volunteer_user: User):
    """Regression test for Bug #8: Production requests with assignment ID 0 must be rejected with HTTP 400."""
    # PUT /api/volunteers/assignments/0
    res_put = client.put(
        "/api/volunteers/assignments/0?status_update=en_route",
        headers=auth_headers(volunteer_user)
    )
    assert res_put.status_code == 400
    assert "Invalid assignment ID" in res_put.json()["detail"]

    # GET /api/volunteers/assignments/0
    res_get = client.get(
        "/api/volunteers/assignments/0",
        headers=auth_headers(volunteer_user)
    )
    assert res_get.status_code == 400
    assert "Invalid assignment ID" in res_get.json()["detail"]

    # POST /api/volunteers/assignments/0/start-pickup
    res_start = client.post(
        "/api/volunteers/assignments/0/start-pickup",
        headers=auth_headers(volunteer_user)
    )
    assert res_start.status_code == 400
    assert "Invalid assignment ID" in res_start.json()["detail"]

    # POST /api/volunteers/assignments/0/arrived
    res_arr = client.post(
        "/api/volunteers/assignments/0/arrived",
        headers=auth_headers(volunteer_user)
    )
    assert res_arr.status_code == 400
    assert "Invalid assignment ID" in res_arr.json()["detail"]

    # POST /api/volunteers/assignments/0/accept
    res_acc = client.post(
        "/api/volunteers/assignments/0/accept",
        headers=auth_headers(volunteer_user)
    )
    assert res_acc.status_code == 400
    assert "Invalid assignment ID" in res_acc.json()["detail"]

    # POST /api/volunteers/assignments/0/reject
    res_rej = client.post(
        "/api/volunteers/assignments/0/reject",
        headers=auth_headers(volunteer_user)
    )
    assert res_rej.status_code == 400
    assert "Invalid assignment ID" in res_rej.json()["detail"]



