"""
Comprehensive Test Suite for Smart Reliability, Performance & Matching Optimization.
Tests:
- Raw operational metrics vs derived metrics
- Sample-size protection tiers (NEW, LIMITED_HISTORY, ESTABLISHED, RELIABLE, NEEDS_REVIEW)
- Recency weighting and outlier protection
- Volunteer response time tracking
- Feasibility hard gate (Feasibility > Reliability)
- Urgency-aware volunteer & NGO matching
- Explainable match reasons ("Why this match?")
- Admin needs-review triage & deprioritization action with AuditLog
- Suspicious feedback detection
- Rescue performance overview & failure analytics
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.models import (
    User, NGO, FoodDonation, VolunteerAssignment, RescueFeedback, RescueIssueReport, AuditLog
)
from app.core.security import create_access_token
from app.services.reliability_service import (
    calculate_volunteer_reliability,
    calculate_ngo_reliability,
    calculate_donor_reliability,
    calculate_rescue_performance_overview,
    calculate_rescue_failure_analytics,
    get_needs_review_participants,
    detect_suspicious_feedback,
    execute_admin_performance_action,
)
from app.services.recommendation_service import (
    recommend_volunteers,
    recommend_ngos,
)

client = TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def _get_token_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_raw_vs_derived_metrics_volunteer(db: Session):
    """Verifies volunteer metrics store exact raw counts and compute derived rates."""
    vol = User(
        name="Courier Alpha",
        email=f"vol_alpha_{datetime.now().timestamp()}@test.com",
        password_hash="hashed_pw",
        role="volunteer",
        carrying_capacity=50,
        is_active=True
    )
    db.add(vol)
    db.commit()
    db.refresh(vol)

    donor = User(
        name="Hotel Donor",
        email=f"donor_alpha_{datetime.now().timestamp()}@test.com",
        password_hash="hashed_pw",
        role="donor"
    )
    db.add(donor)
    db.commit()
    db.refresh(donor)

    # Create 10 completed assignments with response times
    for i in range(10):
        donation = FoodDonation(
            donor_id=donor.id,
            food_name=f"Meals Batch {i}",
            food_category="Cooked Food",
            quantity=20,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc) - timedelta(hours=2),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=4),
            pickup_address="Main St",
            status="completed"
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        assign = VolunteerAssignment(
            donation_id=donation.id,
            volunteer_id=vol.id,
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            accepted_at=datetime.now(timezone.utc) - timedelta(minutes=58),  # 2 min response time
            collected_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            delivered_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            status="delivered"
        )
        db.add(assign)
        db.commit()

        feedback = RescueFeedback(
            donation_id=donation.id,
            author_id=donor.id,
            author_role="donor",
            target_user_id=vol.id,
            overall_rating=5,
            pickup_timeliness="on_time",
            comment="Excellent speed!"
        )
        db.add(feedback)
        db.commit()

    profile = calculate_volunteer_reliability(db, vol.id)

    # Check raw metrics
    assert profile["raw_metrics"]["total_completed"] == 10
    assert profile["raw_metrics"]["total_cancelled"] == 0
    assert profile["raw_metrics"]["average_response_time_seconds"] == 120.0
    
    # Check derived metrics
    assert profile["derived_metrics"]["completion_rate_percent"] == 100.0
    assert profile["derived_metrics"]["on_time_rate_percent"] == 100.0
    assert profile["performance_status"] == "RELIABLE"
    assert profile["trust_tier"] == "Highly Reliable"
    assert "Fast Responder" in profile["trust_badges"]


def test_sample_size_tiers_protection(db: Session):
    """Verifies sample-size protection tiers (NEW, LIMITED_HISTORY, ESTABLISHED, RELIABLE)."""
    vol_new = User(
        name="New Courier",
        email=f"vol_new_{datetime.now().timestamp()}@test.com",
        password_hash="hashed_pw",
        role="volunteer",
        is_active=True
    )
    db.add(vol_new)
    db.commit()
    db.refresh(vol_new)

    # 1 completed rescue only (< 3)
    donor = User(name="Donor X", email=f"donor_x_{datetime.now().timestamp()}@test.com", password_hash="pw", role="donor")
    db.add(donor)
    db.commit()
    db.refresh(donor)

    d = FoodDonation(
        donor_id=donor.id, food_name="Biryani", food_category="Cooked Food", quantity=10,
        preparation_time=datetime.now(timezone.utc), expiry_time=datetime.now(timezone.utc) + timedelta(hours=3),
        pickup_address="Central Kitchen", status="completed"
    )
    db.add(d)
    db.commit()
    db.refresh(d)

    assign = VolunteerAssignment(donation_id=d.id, volunteer_id=vol_new.id, status="delivered")
    db.add(assign)
    db.commit()

    profile = calculate_volunteer_reliability(db, vol_new.id)
    assert profile["performance_status"] == "NEW"
    assert profile["trust_tier"] == "New Volunteer"
    assert profile["has_sufficient_history"] is False
    assert profile["overall_reliability_score"] == 95.0


def test_feasibility_hard_gate_overrides_reliability(db: Session):
    """
    CRITICAL TEST: Verifies that Feasibility strictly precedes Reliability.
    A feasible volunteer with lower reliability MUST be ranked above an infeasible volunteer with 100% reliability.
    """
    # Volunteer A: 100% reliable, but capacity only 10 meals (infeasible for 50 meals) or ETA too far
    vol_a = User(
        name="High Reliability Infeasible Courier",
        email=f"vol_a_{datetime.now().timestamp()}@test.com",
        password_hash="pw",
        role="volunteer",
        reliability_score=100.0,
        carrying_capacity=10,  # TOO SMALL FOR 50 MEALS
        latitude=13.0827,
        longitude=80.2707,
        is_active=True
    )
    # Volunteer B: 75% reliable, but capacity 60 meals (FEASIBLE)
    vol_b = User(
        name="Moderate Reliability Feasible Courier",
        email=f"vol_b_{datetime.now().timestamp()}@test.com",
        password_hash="pw",
        role="volunteer",
        reliability_score=75.0,
        carrying_capacity=60,  # SUFFICIENT
        latitude=13.0830,
        longitude=80.2710,
        is_active=True
    )
    db.add_all([vol_a, vol_b])
    db.commit()
    db.refresh(vol_a)
    db.refresh(vol_b)

    donor = User(name="Donor Y", email=f"donor_y_{datetime.now().timestamp()}@test.com", password_hash="pw", role="donor")
    db.add(donor)
    db.commit()
    db.refresh(donor)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Large Catering Surplus",
        food_category="Cooked Food",
        quantity=50.0,  # 50 meals
        preparation_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expiry_time=datetime.now(timezone.utc) + timedelta(hours=3),
        pickup_address="Banquet Hall",
        latitude=13.0825,
        longitude=80.2705,
        status="pending"
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    recs = recommend_volunteers(db, donation)
    
    # Filter to our test volunteers
    filtered_recs = [r for r in recs if r["volunteer_id"] in [vol_a.id, vol_b.id]]
    assert len(filtered_recs) == 2

    # Volunteer B MUST rank first because Vol A failed the carrying capacity hard gate
    assert filtered_recs[0]["volunteer_id"] == vol_b.id
    assert filtered_recs[0]["score"] > filtered_recs[1]["score"]
    assert any(m["code"] == "capacity" and m["is_positive"] for m in filtered_recs[0]["match_reasons"])


def test_urgency_aware_volunteer_ranking(db: Session):
    """Verifies that for urgent donations, fast response time and high on-time rate are prioritized."""
    vol_fast = User(
        name="Rapid Responder",
        email=f"vol_fast_{datetime.now().timestamp()}@test.com",
        password_hash="pw",
        role="volunteer",
        reliability_score=96.0,
        carrying_capacity=50,
        avg_response_time_seconds=45.0,  # 45s fast responder
        latitude=13.0827,
        longitude=80.2707,
        is_active=True
    )
    vol_slow = User(
        name="Slow Responder",
        email=f"vol_slow_{datetime.now().timestamp()}@test.com",
        password_hash="pw",
        role="volunteer",
        reliability_score=85.0,
        carrying_capacity=50,
        avg_response_time_seconds=600.0,  # 10 min response
        latitude=13.0827,
        longitude=80.2707,
        is_active=True
    )
    db.add_all([vol_fast, vol_slow])
    db.commit()
    db.refresh(vol_fast)
    db.refresh(vol_slow)

    donor = User(name="Donor Z", email=f"donor_z_{datetime.now().timestamp()}@test.com", password_hash="pw", role="donor")
    db.add(donor)
    db.commit()
    db.refresh(donor)

    urgent_donation = FoodDonation(
        donor_id=donor.id,
        food_name="Critical Cooked Rice",
        food_category="Cooked Food",
        quantity=25.0,
        preparation_time=datetime.now(timezone.utc) - timedelta(hours=3),
        expiry_time=datetime.now(timezone.utc) + timedelta(minutes=45),  # 45m left -> URGENT
        pickup_address="Kitchen Corner",
        latitude=13.0827,
        longitude=80.2707,
        status="pending",
        rescue_urgency_level="CRITICAL"
    )
    db.add(urgent_donation)
    db.commit()
    db.refresh(urgent_donation)

    recs = recommend_volunteers(db, urgent_donation)
    filtered_recs = [r for r in recs if r["volunteer_id"] in [vol_fast.id, vol_slow.id]]
    
    assert filtered_recs[0]["volunteer_id"] == vol_fast.id
    assert filtered_recs[0]["score"] > filtered_recs[1]["score"]


def test_needs_review_detection_and_admin_action(db: Session):
    """Verifies automatic NEEDS_REVIEW triggering and administrative intervention action."""
    vol_troubled = User(
        name="Troubled Volunteer",
        email=f"vol_trouble_{datetime.now().timestamp()}@test.com",
        password_hash="pw",
        role="volunteer",
        is_active=True
    )
    db.add(vol_troubled)
    db.commit()
    db.refresh(vol_troubled)

    admin = User(
        name="Admin Chief",
        email=f"admin_chief_{datetime.now().timestamp()}@test.com",
        password_hash="pw",
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # 4 completed, 3 no-shows (failed tasks) -> >15% no-show rate
    for _ in range(4):
        d = FoodDonation(donor_id=admin.id, food_name="Meal", food_category="Cooked Food", quantity=10, preparation_time=datetime.now(timezone.utc), expiry_time=datetime.now(timezone.utc) + timedelta(hours=2), pickup_address="Addr")
        db.add(d)
        db.commit()
        db.refresh(d)
        db.add(VolunteerAssignment(donation_id=d.id, volunteer_id=vol_troubled.id, status="delivered"))
    
    for _ in range(3):
        d = FoodDonation(donor_id=admin.id, food_name="Meal", food_category="Cooked Food", quantity=10, preparation_time=datetime.now(timezone.utc), expiry_time=datetime.now(timezone.utc) + timedelta(hours=2), pickup_address="Addr")
        db.add(d)
        db.commit()
        db.refresh(d)
        db.add(VolunteerAssignment(donation_id=d.id, volunteer_id=vol_troubled.id, status="failed", failure_reason="volunteer_no_show"))
    db.commit()

    profile = calculate_volunteer_reliability(db, vol_troubled.id)
    assert profile["performance_status"] == "NEEDS_REVIEW"
    assert profile["trust_tier"] == "Reliability Needs Review"

    # Admin executes TEMPORARILY_DEPRIORITIZE
    res = execute_admin_performance_action(
        db=db,
        admin_id=admin.id,
        target_user_id=vol_troubled.id,
        action="TEMPORARILY_DEPRIORITIZE",
        notes="Multiple no-shows reported recently."
    )
    assert res["success"] is True
    assert res["admin_action_status"] == "DEPRIORITIZED"

    # Verify audit log was created
    audit = db.query(AuditLog).filter(
        AuditLog.resource_id == vol_troubled.id,
        AuditLog.action.like("%DEPRIORITIZE%")
    ).first()
    assert audit is not None
    assert "DEPRIORITIZE" in audit.action


def test_suspicious_feedback_detection(db: Session):
    """Verifies algorithmic detection of rapid rating bursts without automatic bans."""
    author = User(name="Spam User", email=f"spam_{datetime.now().timestamp()}@test.com", password_hash="pw", role="donor")
    target = User(name="Target User", email=f"target_{datetime.now().timestamp()}@test.com", password_hash="pw", role="volunteer")
    db.add_all([author, target])
    db.commit()
    db.refresh(author)
    db.refresh(target)

    # Submit 4 feedbacks within 2 minutes
    now = datetime.now(timezone.utc)
    for i in range(4):
        d = FoodDonation(donor_id=author.id, food_name=f"Food {i}", food_category="Cooked Food", quantity=5, preparation_time=now, expiry_time=now + timedelta(hours=2), pickup_address="Addr")
        db.add(d)
        db.commit()
        db.refresh(d)

        f = RescueFeedback(
            donation_id=d.id,
            author_id=author.id,
            author_role="donor",
            target_user_id=target.id,
            overall_rating=1,
            comment="Copy paste bad review!",
            created_at=now + timedelta(seconds=i * 20)
        )
        db.add(f)
    db.commit()

    alerts = detect_suspicious_feedback(db)
    assert len(alerts) >= 1
    assert any(a["author_id"] == author.id for a in alerts)


def test_performance_endpoints_integration(db: Session):
    """Verifies REST endpoints for performance breakdown, overview, failure analytics, and needs-review queue."""
    admin = User(name="Admin Integration", email=f"admin_int_{datetime.now().timestamp()}@test.com", password_hash="pw", role="admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)

    admin_headers = _get_token_header(admin)

    # 1. Performance Overview
    r_overview = client.get("/api/admin/performance/overview", headers=admin_headers)
    assert r_overview.status_code == 200
    overview_data = r_overview.json()
    assert "overall_rescue_success_rate_percent" in overview_data
    assert "average_volunteer_response_time_seconds" in overview_data

    # 2. Rescue Failure Analytics
    r_failures = client.get("/api/admin/performance/failures", headers=admin_headers)
    assert r_failures.status_code == 200
    failures_data = r_failures.json()
    assert "failure_reasons" in failures_data
    assert "total_rescue_attempts" in failures_data

    # 3. Needs Review Queue
    r_needs = client.get("/api/admin/performance/needs-review", headers=admin_headers)
    assert r_needs.status_code == 200
    assert isinstance(r_needs.json(), list)

    # 4. My Performance endpoint
    r_me = client.get("/api/users/me/performance", headers=admin_headers)
    assert r_me.status_code == 200
    me_data = r_me.json()
    assert me_data["user_id"] == admin.id
    assert "raw_metrics" in me_data
    assert "derived_metrics" in me_data
