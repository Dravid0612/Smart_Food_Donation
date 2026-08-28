import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db, SessionLocal
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment, RescueFeedback, RescueIssueReport, AuditLog
from app.core.security import hash_password, create_access_token
get_password_hash = hash_password
from app.services.reliability_service import (
    calculate_volunteer_reliability,
    calculate_ngo_reliability,
    calculate_donor_reliability,
    get_participant_reliability
)
from app.services.recommendation_service import recommend_volunteers, recommend_ngos

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_token(email: str, role: str, user_id: int):
    return create_access_token({"sub": str(user_id), "role": role, "email": email})


@pytest.fixture
def rescue_fixture(db_session: Session):
    """Sets up a completed rescue with Donor, NGO, Volunteer, and Admin."""
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    # 1. Admin
    admin = User(
        name="System Admin",
        email=f"admin_{timestamp}@smartfood.org",
        password_hash=get_password_hash("AdminPass123!"),
        role="admin",
        is_active=True
    )
    db_session.add(admin)

    # 2. Donor
    donor = User(
        name="Taj Palace Kitchen",
        email=f"donor_{timestamp}@taj.com",
        password_hash=get_password_hash("DonorPass123!"),
        role="donor",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True,
        donor_trust_score=98.0,
        is_verified_donor=True
    )
    db_session.add(donor)

    # 3. NGO
    ngo_user = User(
        name="Hope Feeding Foundation",
        email=f"ngo_{timestamp}@hope.org",
        password_hash=get_password_hash("NgoPass123!"),
        role="ngo",
        latitude=12.9750,
        longitude=77.6000,
        is_active=True
    )
    db_session.add(ngo_user)
    db_session.flush()

    ngo = NGO(
        user_id=ngo_user.id,
        organization_name="Hope Feeding Foundation",
        address="10 Mission Rd, Bangalore",
        latitude=12.9750,
        longitude=77.6000,
        capacity=200,
        current_capacity=200,
        is_available=True,
        is_verified=True,
        trust_score=96.0
    )
    db_session.add(ngo)

    # 4. Volunteer
    volunteer = User(
        name="Rahul Sharma",
        email=f"vol_{timestamp}@volunteer.org",
        password_hash=get_password_hash("VolPass123!"),
        role="volunteer",
        latitude=12.9720,
        longitude=77.5950,
        carrying_capacity=60,
        reliability_score=95.0,
        is_active=True
    )
    db_session.add(volunteer)

    # 5. Unrelated User (to test authorization rejection)
    unrelated_user = User(
        name="Stranger User",
        email=f"stranger_{timestamp}@other.org",
        password_hash=get_password_hash("StrangerPass123!"),
        role="donor",
        is_active=True
    )
    db_session.add(unrelated_user)
    db_session.flush()

    # 6. Completed Donation
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Buffet Rice & Paneer",
        food_category="Cooked Food",
        quantity=40.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2),
        expiry_time=now + timedelta(hours=4),
        pickup_address="Taj Palace Banquet, MG Road",
        latitude=12.9716,
        longitude=77.5946,
        status="completed",
        assigned_ngo_id=ngo.id,
        assigned_volunteer_id=volunteer.id
    )
    db_session.add(donation)
    db_session.flush()

    # 7. Assignment record
    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer.id,
        status="delivered",
        delivered_at=now
    )
    db_session.add(assignment)
    db_session.commit()

    return {
        "admin": admin,
        "donor": donor,
        "ngo_user": ngo_user,
        "ngo": ngo,
        "volunteer": volunteer,
        "unrelated_user": unrelated_user,
        "donation": donation,
        "assignment": assignment
    }


# ── Test 1: Donor Feedback Submission ────────────────────────────────────────

def test_donor_feedback_submission_success(rescue_fixture):
    data = rescue_fixture
    donor = data["donor"]
    donation = data["donation"]
    token = _get_token(donor.email, "donor", donor.id)

    payload = {
        "overall_rating": 5,
        "pickup_timeliness": "on_time",
        "handover_experience": "smooth",
        "communication_quality": "clear",
        "app_experience": "helpful",
        "comment": "Volunteer Rahul arrived promptly and handled the containers with great care."
    }

    response = client.post(
        f"/api/donations/{donation.id}/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["overall_rating"] == 5
    assert resp_data["pickup_timeliness"] == "on_time"
    assert resp_data["handover_experience"] == "smooth"
    assert resp_data["author_role"] == "donor"
    assert resp_data["donation_id"] == donation.id


# ── Test 2: NGO Feedback Submission ──────────────────────────────────────────

def test_ngo_feedback_submission_success(rescue_fixture):
    data = rescue_fixture
    ngo_user = data["ngo_user"]
    donation = data["donation"]
    token = _get_token(ngo_user.email, "ngo", ngo_user.id)

    payload = {
        "overall_rating": 5,
        "food_condition_rating": "good",
        "quantity_accuracy": "accurate",
        "packaging_quality": "good",
        "volunteer_punctuality": "on_time",
        "volunteer_professionalism": "professional",
        "comment": "Delivered in sealed insulated boxes, ready for immediate meal distribution."
    }

    response = client.post(
        f"/api/donations/{donation.id}/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["food_condition_rating"] == "good"
    assert resp_data["quantity_accuracy"] == "accurate"
    assert resp_data["volunteer_professionalism"] == "professional"
    assert resp_data["author_role"] == "ngo"


# ── Test 3: Volunteer Feedback Submission ────────────────────────────────────

def test_volunteer_feedback_submission_success(rescue_fixture):
    data = rescue_fixture
    volunteer = data["volunteer"]
    donation = data["donation"]
    token = _get_token(volunteer.email, "volunteer", volunteer.id)

    payload = {
        "overall_rating": 5,
        "donor_readiness": "ready",
        "pickup_location_clarity": "easy_to_find",
        "packaging_readiness": "well_packaged",
        "ngo_receiving_readiness": "ready_to_receive",
        "comment": "Smooth pickup at banquet gate and instant intake at NGO shelter."
    }

    response = client.post(
        f"/api/donations/{donation.id}/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["donor_readiness"] == "ready"
    assert resp_data["pickup_location_clarity"] == "easy_to_find"
    assert resp_data["ngo_receiving_readiness"] == "ready_to_receive"
    assert resp_data["author_role"] == "volunteer"


# ── Test 4: Unrelated Participant Rejected ───────────────────────────────────

def test_unrelated_user_cannot_submit_feedback(rescue_fixture):
    data = rescue_fixture
    stranger = data["unrelated_user"]
    donation = data["donation"]
    token = _get_token(stranger.email, "donor", stranger.id)

    payload = {
        "overall_rating": 4,
        "comment": "I was not involved in this rescue."
    }

    response = client.post(
        f"/api/donations/{donation.id}/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert "Only verified participants" in response.json()["detail"]


# ── Test 5: Unauthenticated User Rejected ────────────────────────────────────

def test_unauthenticated_user_rejected(rescue_fixture):
    donation = rescue_fixture["donation"]
    response = client.post(
        f"/api/donations/{donation.id}/feedback",
        json={"overall_rating": 5}
    )
    assert response.status_code == 401


# ── Test 6: Duplicate Feedback Rejected (Abuse Protection) ───────────────────

def test_duplicate_feedback_submission_rejected(rescue_fixture):
    data = rescue_fixture
    donor = data["donor"]
    donation = data["donation"]
    token = _get_token(donor.email, "donor", donor.id)

    payload = {
        "overall_rating": 5,
        "pickup_timeliness": "on_time"
    }

    # First submission
    res1 = client.post(
        f"/api/donations/{donation.id}/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res1.status_code in [201, 409]

    # Second duplicate attempt
    res2 = client.post(
        f"/api/donations/{donation.id}/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res2.status_code == 409
    assert "already submitted feedback" in res2.json()["detail"]


# ── Test 7: Rating Range Validation ──────────────────────────────────────────

def test_rating_range_validation(rescue_fixture):
    data = rescue_fixture
    donor = data["donor"]
    donation = data["donation"]
    token = _get_token(donor.email, "donor", donor.id)

    # Invalid rating > 5
    res = client.post(
        f"/api/donations/{donation.id}/feedback",
        json={"overall_rating": 6},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 422

    # Invalid rating < 1
    res = client.post(
        f"/api/donations/{donation.id}/feedback",
        json={"overall_rating": 0},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 422


# ── Test 8: Comment Length Validation ────────────────────────────────────────

def test_comment_length_validation(rescue_fixture):
    data = rescue_fixture
    donor = data["donor"]
    donation = data["donation"]
    token = _get_token(donor.email, "donor", donor.id)

    long_comment = "A" * 600
    res = client.post(
        f"/api/donations/{donation.id}/feedback",
        json={"overall_rating": 4, "comment": long_comment},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 422


# ── Test 9: Operational Problem Report Creation ──────────────────────────────

def test_report_operational_issue_success(rescue_fixture):
    data = rescue_fixture
    donor = data["donor"]
    donation = data["donation"]
    token = _get_token(donor.email, "donor", donor.id)

    payload = {
        "category": "volunteer_late",
        "description": "Volunteer Rahul arrived 35 minutes after scheduled pickup window.",
        "is_food_safety_incident": False
    }

    response = client.post(
        f"/api/donations/{donation.id}/issues",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["category"] == "volunteer_late"
    assert resp_data["severity"] == "MEDIUM"
    assert resp_data["status"] == "OPEN"
    assert resp_data["donation_id"] == donation.id
    assert resp_data["reporter_role"] == "donor"


# ── Test 10: Critical Food Safety Incident Report ────────────────────────────

def test_critical_food_safety_incident_report(rescue_fixture):
    data = rescue_fixture
    ngo_user = data["ngo_user"]
    donation = data["donation"]
    token = _get_token(ngo_user.email, "ngo", ngo_user.id)

    payload = {
        "category": "food_condition_concern",
        "description": "Food packaging damaged during transit with visible signs of spoilage/temperature compromise.",
        "is_food_safety_incident": True,
        "food_safety_details": "Visible spoilage; unexpected elevated temperature above 25C.",
        "evidence_url": "https://example.com/evidence/damaged_box_123.jpg"
    }

    response = client.post(
        f"/api/donations/{donation.id}/issues",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["category"] == "food_condition_concern"
    assert resp_data["severity"] == "CRITICAL"
    assert resp_data["is_food_safety_incident"] is True
    assert resp_data["status"] == "OPEN"
    assert resp_data["evidence_url"] is not None


# ── Test 11: Admin Feedback Overview Analytics ───────────────────────────────

def test_admin_feedback_overview(rescue_fixture):
    data = rescue_fixture
    admin = data["admin"]
    token = _get_token(admin.email, "admin", admin.id)

    response = client.get(
        "/api/admin/feedback/overview",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    resp_data = response.json()
    assert "total_feedback_count" in resp_data
    assert "average_experience_rating" in resp_data
    assert "open_issues_count" in resp_data
    assert "critical_issues_count" in resp_data
    assert "recent_issues" in resp_data


# ── Test 12: Admin List Issues with Filtering ────────────────────────────────

def test_admin_list_issues_with_filters(rescue_fixture):
    data = rescue_fixture
    admin = data["admin"]
    token = _get_token(admin.email, "admin", admin.id)

    # Filter critical issues
    response = client.get(
        "/api/admin/issues?severity=CRITICAL",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    items = response.json()
    for item in items:
        assert item["severity"] == "CRITICAL"


# ── Test 13: Admin Issue Resolution with Penalty & Audit Log ─────────────────

def test_admin_resolve_issue_with_audit_log(rescue_fixture, db_session: Session):
    data = rescue_fixture
    admin = data["admin"]
    donor = data["donor"]
    volunteer = data["volunteer"]
    donation = data["donation"]

    # Create issue
    issue = RescueIssueReport(
        donation_id=donation.id,
        reporter_id=donor.id,
        reporter_role="donor",
        reported_user_id=volunteer.id,
        category="volunteer_no_show",
        severity="HIGH",
        description="Volunteer Rahul did not arrive for scheduled pickup.",
        status="OPEN",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(issue)
    db_session.commit()
    db_session.refresh(issue)

    token = _get_token(admin.email, "admin", admin.id)

    initial_vol_score = volunteer.reliability_score or 95.0

    resolve_payload = {
        "status": "RESOLVED",
        "admin_notes": "Volunteer contacted; encountered mechanical failure. Applied 2.0 penalty.",
        "reliability_penalty": 2.0
    }

    response = client.post(
        f"/api/admin/issues/{issue.id}/resolve",
        json=resolve_payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["status"] == "RESOLVED"
    assert resp_data["admin_notes"] is not None

    # Check updated volunteer reliability score
    db_session.refresh(volunteer)
    assert volunteer.reliability_score <= initial_vol_score

    # Verify audit log was recorded
    log = db_session.query(AuditLog).filter(
        AuditLog.action == "rescue_issue_resolved",
        AuditLog.resource_id == issue.id
    ).first()
    assert log is not None
    assert log.status == "success"


# ── Test 14: Admin Dismiss Issue ─────────────────────────────────────────────

def test_admin_dismiss_issue(rescue_fixture, db_session: Session):
    data = rescue_fixture
    admin = data["admin"]
    donor = data["donor"]
    donation = data["donation"]

    issue = RescueIssueReport(
        donation_id=donation.id,
        reporter_id=donor.id,
        reporter_role="donor",
        category="other",
        severity="LOW",
        description="App minor visual glitch during confirmation.",
        status="OPEN",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(issue)
    db_session.commit()
    db_session.refresh(issue)

    token = _get_token(admin.email, "admin", admin.id)

    response = client.post(
        f"/api/admin/issues/{issue.id}/dismiss",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["status"] == "DISMISSED"


# ── Test 15: Participant Reliability Calculation with Sample Size Protection ─

def test_participant_reliability_sample_size_protection(db_session: Session):
    # Create brand new volunteer with 1 completed task
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    new_vol = User(
        name="New Volunteer",
        email=f"newvol_{timestamp}@volunteer.org",
        password_hash=get_password_hash("Pass123!"),
        role="volunteer",
        is_active=True
    )
    db_session.add(new_vol)
    db_session.commit()

    profile = calculate_volunteer_reliability(db_session, new_vol.id)

    # 1 task is below MIN_SAMPLE_SIZE_THRESHOLD (3) -> Must return New Volunteer status
    assert profile["has_sufficient_history"] is False
    assert profile["trust_tier"] == "New Volunteer"
    assert "New Volunteer" in profile["trust_badges"]


# ── Test 16: Established Participant Reliability Recency Weighting ───────────

def test_established_volunteer_reliability_and_badges(db_session: Session):
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    donor = User(
        name="Donor User",
        email=f"donor_prof_{timestamp}@food.org",
        password_hash=get_password_hash("Pass123!"),
        role="donor"
    )
    vol = User(
        name="Veteran Volunteer",
        email=f"vetvol_{timestamp}@volunteer.org",
        password_hash=get_password_hash("Pass123!"),
        role="volunteer",
        is_active=True,
        carrying_capacity=50
    )
    db_session.add_all([donor, vol])
    db_session.flush()

    # Create 5 completed assignments with 5-star feedbacks
    now = datetime.now(timezone.utc)
    for i in range(5):
        don = FoodDonation(
            donor_id=donor.id,
            food_name=f"Donation #{i}",
            food_category="Cooked Food",
            quantity=20.0,
            preparation_time=now - timedelta(hours=2),
            expiry_time=now + timedelta(hours=4),
            pickup_address="Test Address",
            status="completed",
            assigned_volunteer_id=vol.id
        )
        db_session.add(don)
        db_session.flush()

        assignment = VolunteerAssignment(
            donation_id=don.id,
            volunteer_id=vol.id,
            status="delivered",
            delivered_at=now
        )
        db_session.add(assignment)

        feedback = RescueFeedback(
            donation_id=don.id,
            author_id=donor.id,
            author_role="donor",
            target_user_id=vol.id,
            overall_rating=5,
            pickup_timeliness="on_time",
            handover_experience="smooth"
        )
        db_session.add(feedback)

    db_session.commit()

    profile = calculate_volunteer_reliability(db_session, vol.id)

    assert profile["has_sufficient_history"] is True
    assert profile["total_completed_rescues"] >= 5
    assert profile["overall_reliability_score"] >= 90.0
    assert profile["trust_tier"] == "Highly Reliable"
    assert any("Reliable Pickup" in b or "High Completion" in b for b in profile["trust_badges"])


# ── Test 17: Matching Precedence (Feasibility Overrides Reliability) ──────────

def test_matching_feasibility_overrides_high_reliability(db_session: Session):
    """
    A highly reliable volunteer (100% reliability) who is 30km away or has insufficient capacity
    must NOT be ranked above a nearby feasible volunteer.
    """
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    now = datetime.now(timezone.utc)

    donor = User(
        name="Urgent Donor",
        email=f"urg_donor_{timestamp}@donor.org",
        password_hash=get_password_hash("Pass123!"),
        role="donor",
        latitude=12.9716,
        longitude=77.5946
    )
    # Volunteer A: Highly reliable (99%), but far away (30km)
    vol_far = User(
        name="Far Volunteer",
        email=f"vol_far_{timestamp}@vol.org",
        password_hash=get_password_hash("Pass123!"),
        role="volunteer",
        latitude=13.2500,  # ~30 km away
        longitude=77.5946,
        carrying_capacity=50,
        reliability_score=99.0,
        is_active=True
    )
    # Volunteer B: Normal reliability (90%), but very close (1km)
    vol_near = User(
        name="Near Volunteer",
        email=f"vol_near_{timestamp}@vol.org",
        password_hash=get_password_hash("Pass123!"),
        role="volunteer",
        latitude=12.9720,  # ~0.1 km away
        longitude=77.5950,
        carrying_capacity=50,
        reliability_score=90.0,
        is_active=True
    )
    db_session.add_all([donor, vol_far, vol_near])
    db_session.flush()

    # Create urgent donation with 30 min window
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Urgent Meals",
        food_category="Cooked Food",
        quantity=30.0,
        preparation_time=now - timedelta(hours=3),
        expiry_time=now + timedelta(minutes=45),
        estimated_window_end=now + timedelta(minutes=45),
        pickup_address="Central Kitchen",
        latitude=12.9716,
        longitude=77.5946,
        status="accepted"
    )
    db_session.add(donation)
    db_session.commit()

    recs = recommend_volunteers(db_session, donation)
    
    # Near volunteer MUST rank above far volunteer despite far volunteer's higher reliability
    near_rec = next(r for r in recs if r["volunteer_id"] == vol_near.id)
    far_rec = next(r for r in recs if r["volunteer_id"] == vol_far.id)

    assert near_rec["score"] > far_rec["score"]


# ── Test 18: Personal Feedback Endpoint & Reliability Endpoint ───────────────

def test_my_feedback_and_user_reliability_endpoints(rescue_fixture):
    data = rescue_fixture
    donor = data["donor"]
    volunteer = data["volunteer"]
    token = _get_token(donor.email, "donor", donor.id)

    # 1. GET /api/feedback/my
    res = client.get(
        "/api/feedback/my",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 2. GET /api/users/{id}/reliability
    res = client.get(
        f"/api/users/{volunteer.id}/reliability",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    rel_data = response = res.json()
    assert "overall_reliability_score" in rel_data
    assert "trust_tier" in rel_data
    assert "dimensions" in rel_data
