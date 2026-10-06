import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment
from app.core.security import hash_password
from app.services.rematching_service import rematching_service
from app.services.proactive_dispatch_service import BackgroundUrgencyMonitor

client = TestClient(app)

def test_head_and_favicon_requests_succeed():
    """Verify HEAD requests on / and /health return 200 OK without 405, and /favicon.ico returns 204."""
    r_root = client.head("/")
    assert r_root.status_code == 200

    r_health = client.head("/health")
    assert r_health.status_code == 200

    r_fav = client.get("/favicon.ico")
    assert r_fav.status_code == 204

def test_collected_donation_rematch_guard(db_session: Session):
    """
    Test that a collected or in-transit food donation:
    1. Returns requires_rematch=False from verify_active_assignment_health when telemetry is stale
    2. Gracefully handles attempt_dynamic_rematch without triggering an illegal state transition to 'volunteer_assigned'
    3. BackgroundUrgencyMonitor.run_cycle executes smoothly without 409 Conflict violations
    """
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp())

    # Donor
    donor = User(
        name=f"Donor Coll {ts}",
        email=f"don_coll_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="donor",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    # Courier
    courier = User(
        name=f"Courier Coll {ts}",
        email=f"cour_coll_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="volunteer",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add_all([donor, courier])
    db_session.commit()

    # Donation in 'collected' state (reproducing Donation #8 scenario)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name=f"Collected Meals {ts}",
        food_category="Cooked Food",
        quantity=50.0,
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="MG Road, Bangalore",
        latitude=donor.latitude,
        longitude=donor.longitude,
        status="collected",
        assigned_volunteer_id=courier.id
    )
    db_session.add(donation)
    db_session.commit()

    # Assignment with stale telemetry
    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=courier.id,
        assigned_at=now - timedelta(minutes=45),
        status="collected",
        last_location_update=now - timedelta(minutes=30)  # > 15 min stale
    )
    db_session.add(assignment)
    db_session.commit()

    # 1. Health check should identify stale telemetry, but NOT trigger dynamic donor rematch
    health = rematching_service.verify_active_assignment_health(db_session, donation, reference_time=now)
    assert health["healthy"] is False
    assert health["trigger"] == "STALE_TELEMETRY"
    assert health["requires_rematch"] is False
    assert donation.feasibility_status == "AT_RISK"

    # 2. Direct attempt_dynamic_rematch invocation should safely refuse post-collection rematch
    rematch_res = rematching_service.attempt_dynamic_rematch(
        db=db_session,
        donation=donation,
        trigger="STALE_TELEMETRY",
        reason="Stale telemetry test"
    )
    assert rematch_res["status"] == "NOT_APPLICABLE_POST_COLLECTION"
    # Status MUST remain 'collected' and never transition illegally to 'volunteer_assigned'
    db_session.refresh(donation)
    assert donation.status == "collected"

    # 3. Urgency Monitor run_cycle should execute across active donations without crashing
    cycle_res = BackgroundUrgencyMonitor.run_cycle(reference_time=now)
    assert cycle_res["status"] == "SUCCESS"
