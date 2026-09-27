import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.models import (
    User,
    NGO,
    FoodDonation,
    Notification,
    MatchOffer,
    VolunteerAssignment,
    DonationHistory,
)
from app.services.proactive_dispatch_service import (
    ProactiveDispatchService,
    BackgroundUrgencyMonitor,
    format_proactive_alert_message,
)
from app.core.security import create_access_token

client = TestClient(app)


def _get_auth_headers(user: User) -> dict:
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
def dispatch_environment(db_session: Session):
    """
    Sets up an isolated, clean test environment for three-wave dispatch verification.
    """
    # 1. Donor
    donor = db_session.query(User).filter(User.email == "dispatch_donor@rescue.org").first()
    if not donor:
        donor = User(
            email="dispatch_donor@rescue.org",
            name="Community Donor",
            password_hash="mock_hash",
            role="donor",
            phone="+919876540001",
            latitude=12.9716,
            longitude=77.5946,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(donor)
        db_session.commit()
        db_session.refresh(donor)

    # 2. NGO 1 (Alpha - Nearest: 1.2km, Capacity: 200 meals, Verified)
    user_ngo1 = db_session.query(User).filter(User.email == "ngo_alpha@rescue.org").first()
    if not user_ngo1:
        user_ngo1 = User(
            email="ngo_alpha@rescue.org",
            name="NGO Alpha Center",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876540002",
            latitude=12.9750,
            longitude=77.5990,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(user_ngo1)
        db_session.commit()
        db_session.refresh(user_ngo1)

    ngo1 = db_session.query(NGO).filter(NGO.user_id == user_ngo1.id).first()
    if not ngo1:
        ngo1 = NGO(
            user_id=user_ngo1.id,
            organization_name="Alpha Rescue Shelter",
            address="Brigade Road, Bangalore",
            latitude=12.9750,
            longitude=77.5990,
            capacity=300,
            current_capacity=200,
            is_verified=True,
            operating_hours="06:00-23:00",
            trust_score=98.0,
        )
        db_session.add(ngo1)
        db_session.commit()
        db_session.refresh(ngo1)

    # 3. NGO 2 (Beta - 3.5km, Capacity: 150 meals, Verified)
    user_ngo2 = db_session.query(User).filter(User.email == "ngo_beta@rescue.org").first()
    if not user_ngo2:
        user_ngo2 = User(
            email="ngo_beta@rescue.org",
            name="NGO Beta Care",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876540003",
            latitude=12.9800,
            longitude=77.6100,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(user_ngo2)
        db_session.commit()
        db_session.refresh(user_ngo2)

    ngo2 = db_session.query(NGO).filter(NGO.user_id == user_ngo2.id).first()
    if not ngo2:
        ngo2 = NGO(
            user_id=user_ngo2.id,
            organization_name="Beta Food Relief",
            address="Indiranagar 100ft Rd, Bangalore",
            latitude=12.9800,
            longitude=77.6100,
            capacity=250,
            current_capacity=150,
            is_verified=True,
            operating_hours="08:00-22:00",
            trust_score=94.0,
        )
        db_session.add(ngo2)
        db_session.commit()
        db_session.refresh(ngo2)

    # 4. Volunteer 1 (Van / Large capacity: 80 meals, 2.0km away, high reliability)
    vol1 = db_session.query(User).filter(User.email == "vol_large@rescue.org").first()
    if not vol1:
        vol1 = User(
            email="vol_large@rescue.org",
            name="Volunteer Large Vehicle",
            password_hash="mock_hash",
            role="volunteer",
            phone="+919876540011",
            latitude=12.9780,
            longitude=77.6000,
            carrying_capacity=80,
            vehicle_type="car",
            reliability_score=97.0,
            avg_response_time_seconds=90.0,
            is_active=True,
        )
        db_session.add(vol1)
        db_session.commit()
        db_session.refresh(vol1)

    # 5. Volunteer 2 (Bike / Small capacity: 20 meals, 0.8km away)
    vol2 = db_session.query(User).filter(User.email == "vol_small@rescue.org").first()
    if not vol2:
        vol2 = User(
            email="vol_small@rescue.org",
            name="Volunteer Small Bike",
            password_hash="mock_hash",
            role="volunteer",
            phone="+919876540012",
            latitude=12.9730,
            longitude=77.5960,
            carrying_capacity=20,
            vehicle_type="bike",
            reliability_score=92.0,
            avg_response_time_seconds=120.0,
            is_active=True,
        )
        db_session.add(vol2)
        db_session.commit()
        db_session.refresh(vol2)

    # Ensure clean reset of locations, capacities and statuses on each test invocation
    user_ngo1.latitude = 12.9716
    user_ngo1.longitude = 77.5946
    ngo1.latitude = 12.9716
    ngo1.longitude = 77.5946
    ngo1.capacity = 500
    ngo1.current_capacity = 500
    ngo1.is_available = True
    ngo1.is_verified = True
    ngo1.trust_score = 100.0
    ngo1.demand_requirements = json.dumps({"Cooked Food": 40, "Bakery": 40, "Packaged Food": 40})
    ngo1.operating_hours = json.dumps({
        day: {"open": "00:00", "close": "23:59", "closed": False}
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    })

    user_ngo2.latitude = 12.9717
    user_ngo2.longitude = 77.5947
    ngo2.latitude = 12.9717
    ngo2.longitude = 77.5947
    ngo2.capacity = 400
    ngo2.current_capacity = 400
    ngo2.is_available = True
    ngo2.is_verified = True
    ngo2.trust_score = 99.5
    ngo2.demand_requirements = json.dumps({"Cooked Food": 40, "Bakery": 40, "Packaged Food": 40})
    ngo2.operating_hours = json.dumps({
        day: {"open": "00:00", "close": "23:59", "closed": False}
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    })

    vol1.latitude = 12.9716
    vol1.longitude = 77.5946
    vol1.is_active = True
    vol1.admin_action_status = "NORMAL"
    vol1.carrying_capacity = 80
    vol1.reliability_score = 99.0

    vol2.latitude = 12.9717
    vol2.longitude = 77.5947
    vol2.is_active = True
    vol2.admin_action_status = "NORMAL"
    vol2.carrying_capacity = 20
    vol2.reliability_score = 95.0
    db_session.commit()

    # 6. Admin
    admin = db_session.query(User).filter(User.email == "admin_dispatch@rescue.org").first()
    if not admin:
        admin = User(
            email="admin_dispatch@rescue.org",
            name="Rescue Admin",
            password_hash="mock_hash",
            role="admin",
            phone="+919876540099",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    return {
        "donor": donor,
        "ngo1": ngo1,
        "user_ngo1": user_ngo1,
        "ngo2": ngo2,
        "user_ngo2": user_ngo2,
        "vol1": vol1,
        "vol2": vol2,
        "admin": admin,
    }


def test_wave_1_ngo_self_pickup_dispatch(db_session: Session, dispatch_environment: dict):
    """
    Wave 1: APPROACHING urgency donation alerts verified NGOs within small radius.
    The offer clearly provides: Food, Quantity, Distance, ERW, Location, Category, Safety advisory.
    """
    donor = dispatch_environment["donor"]
    ngo1 = dispatch_environment["ngo1"]
    user_ngo1 = dispatch_environment["user_ngo1"]

    now = datetime.now(timezone.utc)
    # APPROACHING urgency: ~140 minutes remaining
    prep_time = now - timedelta(hours=1, minutes=10)
    exp_time = now + timedelta(minutes=140)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Vegetable Biryani",
        food_category="Cooked Food",
        quantity=35.0,
        quantity_unit="Meals",
        preparation_time=prep_time,
        expiry_time=exp_time,
        pickup_address="MG Road Food Court, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
        ai_visual_condition="GOOD",
        ai_safety_disclaimer="Safe for consumption within remaining window.",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    result = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=True)

    assert result["status"] == "DISPATCHED"
    assert result["wave"] == 1
    assert result["urgency"] == "APPROACHING"
    assert result["alerted_ngo_count"] >= 1

    # Verify MatchOffer record
    offers = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_type == "ngo"
    ).all()
    assert len(offers) >= 1
    alpha_offer = next((o for o in offers if o.candidate_id == user_ngo1.id), None)
    assert alpha_offer is not None
    assert alpha_offer.status == "offered"
    assert alpha_offer.wave_number == 1
    assert alpha_offer.score > 0

    # Verify Notification to NGO contains complete required information
    notif = db_session.query(Notification).filter(
        Notification.user_id == user_ngo1.id,
        Notification.related_donation_id == donation.id
    ).order_by(Notification.id.desc()).first()

    assert notif is not None
    assert "Vegetable Biryani" in notif.message
    assert "35 Meals" in notif.message
    assert "Cooked Food" in notif.message
    assert "MG Road" in notif.message
    assert "Safety Advisory" in notif.message or "Safe" in notif.message


def test_wave_1_ngo_self_pickup_acceptance_flow(db_session: Session, dispatch_environment: dict):
    """
    Wave 1 Acceptance: NGO accepts for self-pickup:
    - Status transitions to 'accepted' with pickup_mode='self_pickup'.
    - Winning MatchOffer marked 'accepted' with response time recorded.
    - Other offers cancelled.
    - NO volunteer assignment is created.
    - Subsequent acceptance attempts receive 409 Conflict.
    """
    donor = dispatch_environment["donor"]
    ngo1 = dispatch_environment["ngo1"]
    user_ngo1 = dispatch_environment["user_ngo1"]
    user_ngo2 = dispatch_environment["user_ngo2"]

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Steamed Idlis & Sambar",
        food_category="Cooked Food",
        quantity=40.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1, minutes=10),
        expiry_time=now + timedelta(minutes=170),
        pickup_address="Indiranagar Club, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Dispatch Wave 1
    ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=True)

    # NGO 1 accepts with self_pickup
    accept_res = ProactiveDispatchService.process_atomic_ngo_acceptance(
        db_session,
        donation_id=donation.id,
        ngo_user_id=user_ngo1.id,
        reference_time=now + timedelta(seconds=45),
        pickup_mode="self_pickup",
    )

    assert accept_res["status"] == "ACCEPTED"
    assert accept_res["pickup_mode"] == "self_pickup"

    db_session.refresh(donation)
    assert donation.status == "accepted"
    assert donation.assigned_ngo_id == ngo1.id
    assert donation.pickup_mode == "self_pickup"

    # Verify winning offer
    winning_offer = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_id == user_ngo1.id
    ).first()
    assert winning_offer.status == "accepted"
    assert winning_offer.response_time_seconds >= 40.0

    # Verify other offers cancelled
    other_offers = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_id != user_ngo1.id
    ).all()
    for off in other_offers:
        assert off.status == "cancelled"

    # Verify NO volunteer assignment created
    assignments = db_session.query(VolunteerAssignment).filter(
        VolunteerAssignment.donation_id == donation.id
    ).all()
    assert len(assignments) == 0

    # Subsequent acceptance attempt by NGO 2 receives 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        ProactiveDispatchService.process_atomic_ngo_acceptance(
            db_session,
            donation_id=donation.id,
            ngo_user_id=user_ngo2.id,
            reference_time=now + timedelta(seconds=60),
            pickup_mode="self_pickup",
        )
    assert exc_info.value.status_code == 409


def test_wave_1_ngo_pass_and_wave_2_courier_expansion(db_session: Session, dispatch_environment: dict):
    """
    Wave 1 Pass -> Wave 2 Courier Support:
    When an NGO passes or switches to courier dispatch:
    - Candidate MatchOffer marked 'rejected' with response timing.
    - When all Wave 1 NGOs pass, dispatch advances to Wave 2.
    - Feasible volunteers are selected based on capacity and time buffer (never distance alone).
    """
    donor = dispatch_environment["donor"]
    ngo1 = dispatch_environment["ngo1"]
    user_ngo1 = dispatch_environment["user_ngo1"]
    vol1 = dispatch_environment["vol1"]
    vol2 = dispatch_environment["vol2"]

    now = datetime.now(timezone.utc)
    # Quantity = 50 meals (Exceeds vol2 capacity of 20, but fits vol1 capacity of 80)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Curd Rice & Pickle",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2, minutes=30),
        expiry_time=now + timedelta(minutes=90),
        pickup_address="Jayanagar 4th Block, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Initial Wave 1 dispatch
    ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=True)

    # NGO 1 passes via /api/donations/{id}/reject
    headers_ngo1 = _get_auth_headers(user_ngo1)
    reject_resp = client.post(f"/api/donations/{donation.id}/reject?reason=Shelter+capacity+full", headers=headers_ngo1)
    assert reject_resp.status_code == 200

    # Verify NGO 1 MatchOffer updated to rejected
    offer_ngo1 = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_id == user_ngo1.id
    ).first()
    assert offer_ngo1.status == "rejected"
    assert offer_ngo1.responded_at is not None

    # Now simulate volunteer feasibility check: vol1 (capacity 80 >= 50) is eligible, vol2 (capacity 20 < 50) is gated out
    ranked_vols = ProactiveDispatchService.find_and_rank_feasible_volunteers(db_session, donation, reference_time=now)
    ranked_vol_ids = [v["volunteer_id"] for v in ranked_vols]

    assert vol1.id in ranked_vol_ids
    assert vol2.id not in ranked_vol_ids  # Gated out by capacity constraint

    # Force Wave 2 dispatch
    donation.current_alert_wave = 1
    db_session.commit()

    wave2_res = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=True)
    assert wave2_res["wave"] == 2
    assert wave2_res["alerted_volunteer_count"] >= 1

    vol_offers = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_type == "volunteer",
        MatchOffer.wave_number == 2
    ).all()
    assert len(vol_offers) >= 1
    assert any(o.candidate_id == vol1.id for o in vol_offers)


def test_wave_3_critical_emergency_dispatch(db_session: Session, dispatch_environment: dict):
    """
    Wave 3: CRITICAL urgency (< 45m remaining) triggers emergency handling:
    - Jump directly to Wave 3.
    - Sets donation.is_emergency = True.
    - Broadcasts simultaneously to rapid-response NGOs and on-call volunteers.
    - Immediately escalates to Admin.
    - Uses short 5-minute timeout.
    """
    donor = dispatch_environment["donor"]
    admin = dispatch_environment["admin"]

    now = datetime.now(timezone.utc)
    # Critical rescue window: ~40 minutes remaining (< 45m threshold)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Paneer Butter Masala & Roti",
        food_type="Paneer Butter Masala",
        food_category="Cooked Food",
        quantity=25.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=3, minutes=20),
        expiry_time=now + timedelta(minutes=40),
        pickup_address="Commercial Street, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    result = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=True)

    assert result["status"] == "DISPATCHED"
    assert result["wave"] == 3
    assert result["urgency"] == "CRITICAL"
    assert result["timeout_minutes"] == 5

    db_session.refresh(donation)
    assert donation.is_emergency is True
    assert donation.escalated_at is not None

    # Verify Admin received escalation notification
    admin_notif = db_session.query(Notification).filter(
        Notification.user_id == admin.id,
        Notification.related_donation_id == donation.id
    ).first()
    assert admin_notif is not None
    assert "Admin" in admin_notif.title or "Intervention" in admin_notif.title


def test_deduplication_and_cooldown_prevent_duplicate_offers(db_session: Session, dispatch_environment: dict):
    """
    Engine Rule: Deduplication & Cooldown:
    - Cannot send duplicate active offers to candidates who already have status='offered'.
    - Respects cooldown unless urgency increases.
    """
    donor = dispatch_environment["donor"]

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Mixed Veg Pulao",
        food_category="Cooked Food",
        quantity=15.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=1, minutes=10),
        expiry_time=now + timedelta(minutes=170),
        pickup_address="Malleshwaram 8th Cross, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # First dispatch triggers successfully
    res1 = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=False)
    assert res1["status"] == "DISPATCHED"

    offers_after_first = db_session.query(MatchOffer).filter(MatchOffer.donation_id == donation.id).all()
    count_first = len(offers_after_first)
    assert count_first > 0

    # Second dispatch 2 minutes later without urgency change -> blocked by cooldown
    res2 = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now + timedelta(minutes=2), force_dispatch=False)
    assert res2["status"] == "COOLDOWN_ACTIVE"

    offers_after_second = db_session.query(MatchOffer).filter(MatchOffer.donation_id == donation.id).all()
    assert len(offers_after_second) == count_first  # No duplicate offers created


def test_unresponsive_wave_escalation_cycle(db_session: Session, dispatch_environment: dict):
    """
    Tests BackgroundUrgencyMonitor and check_and_escalate_unresponsive_waves:
    - When a wave times out without response, previous offers are expired and next wave is triggered.
    """
    donor = dispatch_environment["donor"]

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Chapati & Dal Fry",
        food_category="Cooked Food",
        quantity=30.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=3, minutes=30),
        expiry_time=now + timedelta(minutes=150),
        pickup_address="Rajajinagar 1st Block, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Dispatch Wave 1
    ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now, force_dispatch=True)
    assert donation.current_alert_wave == 1

    # Fast forward past wave_timeout_at
    future_time = donation.wave_timeout_at + timedelta(minutes=1)

    escalations = ProactiveDispatchService.check_and_escalate_unresponsive_waves(db_session, reference_time=future_time)

    assert len(escalations) >= 1
    db_session.refresh(donation)
    assert donation.current_alert_wave >= 2

    # Verify Wave 1 offers were marked 'expired'
    w1_offers = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.wave_number == 1
    ).all()
    for o in w1_offers:
        assert o.status == "expired"


def test_rescue_window_ended_halts_dispatch(db_session: Session, dispatch_environment: dict):
    """
    Engine Rule: Live ERW re-evaluation:
    If rescue window has ended, dispatch halts, outstanding offers cancelled, donation marked expired.
    """
    donor = dispatch_environment["donor"]

    now = datetime.now(timezone.utc)
    # Expired donation
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Stale Cooked Rice",
        food_category="Cooked Food",
        quantity=10.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=6),
        expiry_time=now - timedelta(minutes=10),
        pickup_address="BTM Layout, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    result = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now)
    assert result["status"] == "WINDOW_ENDED"

    db_session.refresh(donation)
    assert donation.status == "expired"
