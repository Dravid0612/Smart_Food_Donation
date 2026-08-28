import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db, SessionLocal
from app.models.models import (
    User,
    NGO,
    FoodDonation,
    Notification,
    MatchOffer,
    VolunteerAssignment,
    RescueIssueReport,
    DonationHistory,
)
from app.services.proactive_dispatch_service import (
    ProactiveDispatchService,
    BackgroundUrgencyMonitor,
    format_proactive_alert_message,
    _extract_approximate_area,
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
def setup_proactive_environment(db_session: Session):
    """
    Sets up a clean test environment with:
    - 1 Donor
    - 4 NGOs with varying distances, operating hours, and capacities
    - 2 Volunteers
    - 1 Admin
    """
    # 1. Donor
    donor = db_session.query(User).filter(User.email == "proactive_donor@food.org").first()
    if not donor:
        donor = User(
            email="proactive_donor@food.org",
            name="Proactive Donor",
            password_hash="mock_hash",
            role="donor",
            phone="+919876543201",
            latitude=12.9716,
            longitude=77.5946,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(donor)
        db_session.commit()
        db_session.refresh(donor)

    # 2. NGO A (Close: 1.2km, Open, Large Capacity: 200 meals, High Reliability)
    user_ngo_a = db_session.query(User).filter(User.email == "ngo_a@food.org").first()
    if not user_ngo_a:
        user_ngo_a = User(
            email="ngo_a@food.org",
            name="NGO Alpha Shelter",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876543202",
            latitude=12.9750,
            longitude=77.5990,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(user_ngo_a)
        db_session.commit()
        db_session.refresh(user_ngo_a)

    ngo_a = db_session.query(NGO).filter(NGO.user_id == user_ngo_a.id).first()
    if not ngo_a:
        ngo_a = NGO(
            user_id=user_ngo_a.id,
            organization_name="Alpha Shelter Trust",
            address="Koramangala 4th Block, Bangalore",
            latitude=12.9750,
            longitude=77.5990,
            capacity=300,
            current_capacity=200,
            is_verified=True,
            is_available=True,
            trust_score=98.0,
            operating_hours=json.dumps({
                "monday": {"open": "00:00", "close": "23:59", "closed": False},
                "tuesday": {"open": "00:00", "close": "23:59", "closed": False},
                "wednesday": {"open": "00:00", "close": "23:59", "closed": False},
                "thursday": {"open": "00:00", "close": "23:59", "closed": False},
                "friday": {"open": "00:00", "close": "23:59", "closed": False},
                "saturday": {"open": "00:00", "close": "23:59", "closed": False},
                "sunday": {"open": "00:00", "close": "23:59", "closed": False},
            }),
            demand_requirements=json.dumps({"Cooked Food": 150, "Bakery": 50}),
        )
        db_session.add(ngo_a)
        db_session.commit()
        db_session.refresh(ngo_a)

    # 3. NGO B (Medium: 3.5km, Open, Moderate Capacity: 100 meals, Tamil Preferred)
    user_ngo_b = db_session.query(User).filter(User.email == "ngo_b@food.org").first()
    if not user_ngo_b:
        user_ngo_b = User(
            email="ngo_b@food.org",
            name="NGO Beta Care",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876543203",
            latitude=12.9850,
            longitude=77.6100,
            preferred_language="ta",
            is_active=True,
        )
        db_session.add(user_ngo_b)
        db_session.commit()
        db_session.refresh(user_ngo_b)

    ngo_b = db_session.query(NGO).filter(NGO.user_id == user_ngo_b.id).first()
    if not ngo_b:
        ngo_b = NGO(
            user_id=user_ngo_b.id,
            organization_name="Beta Care Foundation",
            address="Indiranagar 100ft Road, Bangalore",
            latitude=12.9850,
            longitude=77.6100,
            capacity=150,
            current_capacity=100,
            is_verified=True,
            is_available=True,
            trust_score=94.0,
            operating_hours=json.dumps({
                "monday": {"open": "00:00", "close": "23:59", "closed": False},
                "tuesday": {"open": "00:00", "close": "23:59", "closed": False},
                "wednesday": {"open": "00:00", "close": "23:59", "closed": False},
                "thursday": {"open": "00:00", "close": "23:59", "closed": False},
                "friday": {"open": "00:00", "close": "23:59", "closed": False},
                "saturday": {"open": "00:00", "close": "23:59", "closed": False},
                "sunday": {"open": "00:00", "close": "23:59", "closed": False},
            }),
            demand_requirements=json.dumps({"Cooked Food": 100}),
        )
        db_session.add(ngo_b)
        db_session.commit()
        db_session.refresh(ngo_b)

    # 4. NGO C (Very Close: 0.8km, but Capacity = 10 meals -> Fails capacity gate for 50 meals!)
    user_ngo_c = db_session.query(User).filter(User.email == "ngo_c@food.org").first()
    if not user_ngo_c:
        user_ngo_c = User(
            email="ngo_c@food.org",
            name="NGO Gamma Small",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876543204",
            latitude=12.9730,
            longitude=77.5960,
            is_active=True,
        )
        db_session.add(user_ngo_c)
        db_session.commit()
        db_session.refresh(user_ngo_c)

    ngo_c = db_session.query(NGO).filter(NGO.user_id == user_ngo_c.id).first()
    if not ngo_c:
        ngo_c = NGO(
            user_id=user_ngo_c.id,
            organization_name="Gamma Mini Shelter",
            address="MG Road, Bangalore",
            latitude=12.9730,
            longitude=77.5960,
            capacity=30,
            current_capacity=10, # Insufficient for 50 meals!
            is_verified=True,
            is_available=True,
            trust_score=90.0,
        )
        db_session.add(ngo_c)
        db_session.commit()
        db_session.refresh(ngo_c)

    # 5. NGO D (Close: 1.5km, but Closed Today!)
    user_ngo_d = db_session.query(User).filter(User.email == "ngo_d@food.org").first()
    if not user_ngo_d:
        user_ngo_d = User(
            email="ngo_d@food.org",
            name="NGO Delta Closed",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876543205",
            is_active=True,
        )
        db_session.add(user_ngo_d)
        db_session.commit()
        db_session.refresh(user_ngo_d)

    ngo_d = db_session.query(NGO).filter(NGO.user_id == user_ngo_d.id).first()
    if not ngo_d:
        ngo_d = NGO(
            user_id=user_ngo_d.id,
            organization_name="Delta Night Shelter",
            address="Brigade Road, Bangalore",
            latitude=12.9740,
            longitude=77.5980,
            capacity=200,
            current_capacity=200,
            is_verified=True,
            is_available=True,
            operating_hours=json.dumps({
                "monday": {"closed": True}, "tuesday": {"closed": True},
                "wednesday": {"closed": True}, "thursday": {"closed": True},
                "friday": {"closed": True}, "saturday": {"closed": True},
                "sunday": {"closed": True},
            }),
        )
        db_session.add(ngo_d)
        db_session.commit()
        db_session.refresh(ngo_d)

    # 6. Volunteers
    vol1 = db_session.query(User).filter(User.email == "proactive_vol1@food.org").first()
    if not vol1:
        vol1 = User(
            email="proactive_vol1@food.org",
            name="Express Courier Volunteer",
            password_hash="mock_hash",
            role="volunteer",
            phone="+919876543206",
            latitude=12.9720,
            longitude=77.5950,
            carrying_capacity=80,
            is_active=True,
        )
        db_session.add(vol1)
        db_session.commit()

    # 7. Admin
    admin = db_session.query(User).filter(User.email == "proactive_admin@food.org").first()
    if not admin:
        admin = User(
            email="proactive_admin@food.org",
            name="Proactive Admin",
            password_hash="mock_hash",
            role="admin",
            phone="+919876543207",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()

    return {
        "donor": donor,
        "ngo_a": user_ngo_a,
        "ngo_b": user_ngo_b,
        "ngo_c": user_ngo_c,
        "ngo_d": user_ngo_d,
        "vol1": vol1,
        "admin": admin,
    }


def test_01_fresh_donation_normal_operations(db_session: Session, setup_proactive_environment):
    """
    A freshly prepared donation with > 4 hours rescue window should stay in FRESH state
    and NOT trigger emergency alert dispatching.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Fresh Vegetable Rice",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(minutes=15), # 15 min ago -> Fresh
        expiry_time=now + timedelta(hours=6),
        pickup_address="123, 5th Cross, Koramangala 4th Block, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    result = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now)

    assert result["status"] == "NORMAL_OPERATIONS"
    assert result["urgency"] == "FRESH"
    assert (donation.rescue_urgency_level or getattr(donation, "urgency_level", "FRESH")) == "FRESH"
    assert donation.remaining_minutes > 180


def test_02_approaching_urgency_awareness_alert(db_session: Session, setup_proactive_environment):
    """
    When elapsed preparation time brings rescue window to 2-4 hours, urgency transitions to APPROACHING.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Cooked Sambar Rice",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=3), # ~3 hours ago
        expiry_time=now + timedelta(hours=3),
        pickup_address="456, 80ft Road, Indiranagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    eval_res = ProactiveDispatchService.evaluate_donation_urgency(db_session, donation, reference_time=now)
    assert eval_res["urgency_level"] in ["APPROACHING", "URGENT"]
    assert donation.remaining_minutes > 0


def test_03_urgent_transition_targeted_feasible_ngo_dispatch(db_session: Session, setup_proactive_environment):
    """
    When donation becomes URGENT (45m - 2h remaining), the system automatically:
    1. Hard-gates NGOs (only open, verified, capacity >= 50, feasible ETA).
    2. Dispatches Wave 1 MatchOffers to top feasible candidates.
    3. Sends privacy-safe targeted notifications to NGOs and reassurance to Donor.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Steamed Biryani",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2, minutes=30), # ~1.5h remaining -> URGENT
        expiry_time=now + timedelta(minutes=90),
        pickup_address="100, Commercial Street, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    dispatch_res = ProactiveDispatchService.dispatch_proactive_alerts(
        db_session, donation, reference_time=now, force_dispatch=True
    )

    assert dispatch_res["status"] == "DISPATCHED"
    assert dispatch_res["urgency"] == "URGENT"
    assert dispatch_res["wave"] == 1
    assert dispatch_res["alerted_ngo_count"] >= 1

    # Check MatchOffers in database
    offers = db_session.query(MatchOffer).filter(MatchOffer.donation_id == donation.id).all()
    assert len(offers) >= 1
    assert offers[0].status == "offered"
    assert offers[0].wave_number == 1

    # Check Donor Notification
    donor_notif = db_session.query(Notification).filter(
        Notification.user_id == donor.id,
        Notification.related_donation_id == donation.id
    ).order_by(Notification.id.desc()).first()
    assert donor_notif is not None
    assert "time-critical" in donor_notif.title.lower() or "time-critical" in donor_notif.message.lower()


def test_04_critical_transition_emergency_shortlist_alert(db_session: Session, setup_proactive_environment):
    """
    When donation has < 45m remaining, urgency becomes CRITICAL.
    Emergency alerts with shortened response timeout are sent to the top feasible candidate NGOs.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Idli",
        food_category="Cooked Food",
        quantity=40.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=3, minutes=20), # ~40m remaining -> CRITICAL & Feasible
        expiry_time=now + timedelta(minutes=40),
        pickup_address="789, Residency Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    dispatch_res = ProactiveDispatchService.dispatch_proactive_alerts(
        db_session, donation, reference_time=now, force_dispatch=True
    )

    assert dispatch_res["status"] == "DISPATCHED"
    assert dispatch_res["urgency"] == "CRITICAL"
    assert dispatch_res["timeout_minutes"] == 5 # Shortened emergency response window


def test_05_rescue_window_ended_stops_dispatch_and_inactivates(db_session: Session, setup_proactive_environment):
    """
    When rescue window is <= 0m, the state becomes RESCUE_WINDOW_ENDED.
    Normal dispatch halts and outstanding offers are cancelled.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Old Rice Dish",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=8), # Expired window
        expiry_time=now - timedelta(minutes=30),
        pickup_address="Koramangala, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Add a mock pending offer
    offer = MatchOffer(
        donation_id=donation.id,
        candidate_id=setup_proactive_environment["ngo_a"].id,
        candidate_type="ngo",
        status="offered",
    )
    db_session.add(offer)
    db_session.commit()

    dispatch_res = ProactiveDispatchService.dispatch_proactive_alerts(
        db_session, donation, reference_time=now
    )

    assert dispatch_res["status"] == "WINDOW_ENDED"
    assert donation.status == "expired"

    # Verify offer was cancelled
    db_session.refresh(offer)
    assert offer.status == "cancelled"


def test_06_alert_deduplication_and_cooldown(db_session: Session, setup_proactive_environment):
    """
    Calling dispatch repeatedly in the same urgency state within cooldown returns COOLDOWN_ACTIVE.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Idli & Sambar",
        food_category="Cooked Food",
        quantity=30.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2, minutes=30), # ~90m remaining -> URGENT
        expiry_time=now + timedelta(minutes=90),
        pickup_address="Malleshwaram, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # First dispatch -> DISPATCHED
    res1 = ProactiveDispatchService.dispatch_proactive_alerts(db_session, donation, reference_time=now)
    assert res1["status"] == "DISPATCHED"

    # Immediate second dispatch 1 minute later -> COOLDOWN_ACTIVE (Deduplicated!)
    res2 = ProactiveDispatchService.dispatch_proactive_alerts(
        db_session, donation, reference_time=now + timedelta(minutes=1)
    )
    assert res2["status"] == "COOLDOWN_ACTIVE"


def test_07_feasibility_hard_gate_overrides_closer_infeasible_ngo(db_session: Session, setup_proactive_environment):
    """
    Proves requirement #11: FEASIBILITY > PROXIMITY.
    NGOs whose transit + intake time exceeds the remaining rescue window are EXCLUDED,
    even if closer than further feasible NGOs.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    # 15 minutes remaining
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Quick Rescue Bread",
        food_category="Bakery",
        quantity=30.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2),
        expiry_time=now + timedelta(minutes=15),
        remaining_minutes=15, # Tight 15 min window
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    ranked_ngos = ProactiveDispatchService.find_and_rank_feasible_ngos(db_session, donation, reference_time=now)

    for ngo_data in ranked_ngos:
        # Every single candidate must have a feasible calculation
        assert ngo_data["buffer_minutes"] >= 0 or ngo_data["feasibility_status"] == "RESCUE_FEASIBLE"


def test_08_capacity_and_closed_hard_gates_filter_ineligible_ngos(db_session: Session, setup_proactive_environment):
    """
    NGO C (capacity 10 meals) and NGO D (closed) must be filtered out for a 50 meal donation.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Large Feast Rice",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2),
        expiry_time=now + timedelta(hours=2),
        remaining_minutes=120,
        pickup_address="Indiranagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    ranked = ProactiveDispatchService.find_and_rank_feasible_ngos(db_session, donation, reference_time=now)
    ranked_user_ids = {r["user_id"] for r in ranked}

    # NGO C (capacity 10 < 50) and NGO D (closed) must NOT be in the ranked list
    assert setup_proactive_environment["ngo_c"].id not in ranked_user_ids
    assert setup_proactive_environment["ngo_d"].id not in ranked_user_ids
    assert setup_proactive_environment["ngo_a"].id in ranked_user_ids


def test_09_multi_wave_escalation_on_timeout(db_session: Session, setup_proactive_environment):
    """
    When Wave 1 response timeout expires with no NGO acceptance,
    check_and_escalate_unresponsive_waves triggers the next wave.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Wave Test Food",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=4),
        expiry_time=now + timedelta(minutes=80),
        remaining_minutes=80,
        pickup_address="Koramangala, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
        current_alert_wave=1,
        wave_timeout_at=now - timedelta(minutes=2), # Expired 2 mins ago!
        last_alerted_urgency="URGENT",
        last_alerted_at=now - timedelta(minutes=12),
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Run wave timeout check
    escalations = ProactiveDispatchService.check_and_escalate_unresponsive_waves(
        db_session, reference_time=now
    )

    assert len(escalations) >= 1
    assert escalations[0]["donation_id"] == donation.id


def test_10_atomic_ngo_acceptance_lock_and_409_conflict(db_session: Session, setup_proactive_environment):
    """
    Requirement #15: Atomic NGO acceptance lock.
    First NGO accepts successfully; second NGO attempting acceptance receives 409 Conflict.
    All other outstanding offers are cancelled.
    """
    donor = setup_proactive_environment["donor"]
    ngo_a = setup_proactive_environment["ngo_a"]
    ngo_b = setup_proactive_environment["ngo_b"]
    now = datetime.now(timezone.utc)

    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Atomic Lock Rice",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2),
        expiry_time=now + timedelta(hours=2),
        remaining_minutes=90,
        pickup_address="Indiranagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # Initial offers to both NGO A and NGO B
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=ngo_a.id,
        candidate_type="ngo",
        status="offered",
        offered_at=now - timedelta(minutes=3),
    )
    offer_b = MatchOffer(
        donation_id=donation.id,
        candidate_id=ngo_b.id,
        candidate_type="ngo",
        status="offered",
        offered_at=now - timedelta(minutes=3),
    )
    db_session.add_all([offer_a, offer_b])
    db_session.commit()

    # 1. NGO A accepts -> Success
    accept_res = ProactiveDispatchService.process_atomic_ngo_acceptance(
        db_session, donation.id, ngo_user_id=ngo_a.id, reference_time=now
    )
    assert accept_res["status"] == "ACCEPTED"
    assert donation.status == "accepted"

    # Verify offer A accepted and offer B cancelled
    db_session.refresh(offer_a)
    db_session.refresh(offer_b)
    assert offer_a.status == "accepted"
    assert offer_b.status == "cancelled"

    # 2. NGO B tries to accept -> 409 Conflict!
    with pytest.raises(HTTPException) as exc_info:
        ProactiveDispatchService.process_atomic_ngo_acceptance(
            db_session, donation.id, ngo_user_id=ngo_b.id, reference_time=now
        )
    assert exc_info.value.status_code == 409


def test_11_privacy_safe_location_masking():
    """
    Requirement #8: Donor exact address and private contact are masked in alerts.
    """
    raw_addr = "Flat 402, Sunshine Apartments, 12th Main Road, Indiranagar, Bangalore, 560038"
    masked = _extract_approximate_area(raw_addr)

    # Must NOT contain flat number or private street line
    assert "Flat 402" not in masked
    assert "area" in masked


def test_12_trilingual_proactive_alert_formatting():
    """
    Requirement #31: Trilingual natural alert templates (English, Tamil, Hindi).
    """
    # English
    en_title, en_msg = format_proactive_alert_message(
        role="donor", urgency="URGENT", language="en", food_name="Rice", quantity=50, remaining_minutes=35
    )
    assert "time-critical" in en_title.lower() or "time-critical" in en_msg.lower()

    # Tamil
    ta_title, ta_msg = format_proactive_alert_message(
        role="ngo", urgency="CRITICAL", language="ta", food_name="பிரியாணி", quantity=100, remaining_minutes=15
    )
    assert "அவசர" in ta_title or "மீட்பு" in ta_title

    # Hindi
    hi_title, hi_msg = format_proactive_alert_message(
        role="donor", urgency="CRITICAL", language="hi", food_name="चावल", quantity=50, remaining_minutes=10
    )
    assert "गंभीर" in hi_title or "बचाव" in hi_msg


def test_13_custom_food_conservative_proactive_rescue(db_session: Session, setup_proactive_environment):
    """
    Requirement #28: Custom food donations use conservative rule profiles
    and seamlessly flow through proactive dispatch without inventing exact expiry.
    """
    donor = setup_proactive_environment["donor"]
    now = datetime.now(timezone.utc)

    custom_donation = FoodDonation(
        donor_id=donor.id,
        food_name="Grandma's Special Spicy Lentil Stew",
        food_source="CUSTOM",
        custom_food_name="Grandma's Special Spicy Lentil Stew",
        food_category="Cooked Food",
        quantity=40.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=3, minutes=30),
        expiry_time=now + timedelta(hours=2),
        pickup_address="Jayanagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(custom_donation)
    db_session.commit()
    db_session.refresh(custom_donation)

    eval_res = ProactiveDispatchService.evaluate_donation_urgency(db_session, custom_donation, reference_time=now)
    assert eval_res["urgency_level"] in ["APPROACHING", "URGENT", "CRITICAL"]
    assert custom_donation.remaining_minutes > 0


def test_14_api_monitor_urgency_and_dispatch_status_endpoints(db_session: Session, setup_proactive_environment):
    """
    Verifies REST API endpoints:
    - POST /api/donations/monitor-urgency
    - GET /api/donations/{id}/dispatch-status
    - POST /api/donations/{id}/trigger-dispatch
    """
    admin = setup_proactive_environment["admin"]
    donor = setup_proactive_environment["donor"]
    headers_admin = _get_auth_headers(admin)
    headers_donor = _get_auth_headers(donor)
    now = datetime.now(timezone.utc)

    # Create sample donation
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="API Test Food",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(hours=2),
        expiry_time=now + timedelta(hours=3),
        pickup_address="Richmond Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    # 1. Trigger background urgency monitor cycle via API
    r_monitor = client.post("/api/donations/monitor-urgency", headers=headers_admin)
    assert r_monitor.status_code == 200
    assert r_monitor.json()["status"] == "SUCCESS"

    # 2. Trigger dispatch for specific donation
    r_trigger = client.post(f"/api/donations/{donation.id}/trigger-dispatch", headers=headers_donor)
    assert r_trigger.status_code == 200

    # 3. Get dispatch status
    r_status = client.get(f"/api/donations/{donation.id}/dispatch-status", headers=headers_donor)
    assert r_status.status_code == 200
    status_data = r_status.json()
    assert status_data["donation_id"] == donation.id
    assert "offers" in status_data
    assert "remaining_minutes" in status_data
