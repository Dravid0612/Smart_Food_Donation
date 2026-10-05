import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
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
    AuditLog,
)
from app.core.security import create_access_token
from app.services.proactive_dispatch_service import ProactiveDispatchService

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
def p4_environment(db_session: Session):
    """
    Sets up isolated donor, two verified NGOs, and a volunteer for Phase 4 tests.
    """
    # 1. Donor
    donor = db_session.query(User).filter(User.email == "p4_donor@rescue.org").first()
    if not donor:
        donor = User(
            email="p4_donor@rescue.org",
            name="Phase 4 Donor",
            password_hash="mock_hash",
            role="donor",
            phone="+919876541101",
            latitude=12.9716,
            longitude=77.5946,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(donor)
        db_session.commit()
        db_session.refresh(donor)

    # 2. NGO Alpha (Self-pickup capable shelter)
    user_ngo_a = db_session.query(User).filter(User.email == "p4_ngo_alpha@rescue.org").first()
    if not user_ngo_a:
        user_ngo_a = User(
            email="p4_ngo_alpha@rescue.org",
            name="NGO Alpha Self-Pickup",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876541102",
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
            organization_name="Alpha Community Kitchen",
            address="Brigade Road, Bangalore",
            latitude=12.9750,
            longitude=77.5990,
            capacity=300,
            current_capacity=200,
            is_verified=True,
            operating_hours="06:00-23:00",
            trust_score=98.0,
        )
        db_session.add(ngo_a)
        db_session.commit()
        db_session.refresh(ngo_a)
    else:
        ngo_a.current_capacity = 200
        ngo_a.is_verified = True
        db_session.commit()

    # 3. NGO Beta (Competing shelter)
    user_ngo_b = db_session.query(User).filter(User.email == "p4_ngo_beta@rescue.org").first()
    if not user_ngo_b:
        user_ngo_b = User(
            email="p4_ngo_beta@rescue.org",
            name="NGO Beta Care",
            password_hash="mock_hash",
            role="ngo",
            phone="+919876541103",
            latitude=12.9800,
            longitude=77.6100,
            preferred_language="en",
            is_active=True,
        )
        db_session.add(user_ngo_b)
        db_session.commit()
        db_session.refresh(user_ngo_b)

    ngo_b = db_session.query(NGO).filter(NGO.user_id == user_ngo_b.id).first()
    if not ngo_b:
        ngo_b = NGO(
            user_id=user_ngo_b.id,
            organization_name="Beta Food Relief",
            address="Indiranagar 100ft Rd, Bangalore",
            latitude=12.9800,
            longitude=77.6100,
            capacity=250,
            current_capacity=150,
            is_verified=True,
            operating_hours="08:00-22:00",
            trust_score=95.0,
        )
        db_session.add(ngo_b)
        db_session.commit()
        db_session.refresh(ngo_b)
    else:
        ngo_b.current_capacity = 150
        ngo_b.is_verified = True
        db_session.commit()

    # 4. Volunteer
    vol = db_session.query(User).filter(User.email == "p4_volunteer@rescue.org").first()
    if not vol:
        vol = User(
            email="p4_volunteer@rescue.org",
            name="Phase 4 Volunteer Courier",
            password_hash="mock_hash",
            role="volunteer",
            phone="+919876541111",
            latitude=12.9760,
            longitude=77.6000,
            carrying_capacity=80,
            vehicle_type="bike",
            reliability_score=97.0,
            completed_deliveries=15,
            is_active=True,
        )
        db_session.add(vol)
        db_session.commit()
        db_session.refresh(vol)
    else:
        # Clear existing active assignments for test isolation
        db_session.query(VolunteerAssignment).filter(VolunteerAssignment.volunteer_id == vol.id).delete()
        db_session.commit()

    return {
        "donor": donor,
        "user_ngo_a": user_ngo_a,
        "ngo_a": ngo_a,
        "user_ngo_b": user_ngo_b,
        "ngo_b": ngo_b,
        "volunteer": vol,
    }


from app.services.otp_service import generate_pickup_otp

def _create_fresh_donation(db: Session, donor: User, food_name: str = "Surplus Rice & Curry", quantity: float = 30.0) -> FoodDonation:
    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name=food_name,
        food_category="Cooked Meals",
        quantity=quantity,
        quantity_unit="meals",
        preparation_time=now - timedelta(hours=1),
        expiry_time=now + timedelta(hours=3),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pending",
        remaining_minutes=150.0,
        current_alert_wave=1,
        otp_expiry=now + timedelta(hours=4),
        pickup_mode="volunteer_dispatch",
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)
    plaintext_otp, _ = generate_pickup_otp(db, donation, donor)
    donation.verification_otp = plaintext_otp
    db.commit()
    db.refresh(donation)
    return donation


# ==============================================================================
# TEST 1: NGO Self-Pickup Clean Branch Acceptance & Offer Lifecycle
# ==============================================================================
def test_01_ngo_self_pickup_clean_branch_acceptance(db_session: Session, p4_environment: dict):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    ngo_a = p4_environment["ngo_a"]
    user_ngo_b = p4_environment["user_ngo_b"]
    ngo_b = p4_environment["ngo_b"]

    donation = _create_fresh_donation(db_session, donor, "P4 Biryani Batch", quantity=40.0)
    now = datetime.now(timezone.utc)

    # Simulate Wave 1 offers dispatched to both NGO Alpha and NGO Beta
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        score=95.0,
        status="offered",
        wave_number=1,
        offered_at=now - timedelta(minutes=2),
    )
    offer_b = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_b.id,
        candidate_type="ngo",
        score=90.0,
        status="offered",
        wave_number=1,
        offered_at=now - timedelta(minutes=2),
    )
    db_session.add_all([offer_a, offer_b])
    db_session.commit()
    db_session.refresh(offer_a)
    db_session.refresh(offer_b)

    # NGO Alpha accepts with self-pickup choice
    headers = _get_auth_headers(user_ngo_a)
    payload = {
        "pickup_mode": "self_pickup",
        "offer_id": offer_a.id,
        "remarks": "NGO Alpha collecting directly with shelter vehicle"
    }
    response = client.post(f"/api/donations/{donation.id}/accept", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["status"] == "accepted"
    assert data["pickup_mode"] == "self_pickup"
    assert data["assigned_ngo_id"] == ngo_a.id

    # Verify winning offer updated
    db_session.refresh(offer_a)
    assert offer_a.status == "accepted"
    assert offer_a.responded_at is not None
    assert offer_a.response_time_seconds is not None
    assert offer_a.response_time_seconds >= 120.0  # offered 2 min ago

    # Verify competing offer cancelled
    db_session.refresh(offer_b)
    assert offer_b.status == "cancelled"
    assert offer_b.responded_at is not None

    # Verify donation row updated
    db_session.refresh(donation)
    assert donation.status == "accepted"
    assert donation.pickup_mode == "self_pickup"
    assert donation.assigned_ngo_id == ngo_a.id
    assert donation.assigned_volunteer_id is None

    # Verify capacity deducted
    db_session.refresh(ngo_a)
    assert ngo_a.current_capacity == 160.0  # 200 - 40

    # Verify DonationHistory recorded
    history = db_session.query(DonationHistory).filter(
        DonationHistory.donation_id == donation.id,
        DonationHistory.new_status == "accepted"
    ).first()
    assert history is not None
    assert history.changed_by == user_ngo_a.id
    assert "Self-Pickup" in history.remarks

    # Verify donor notification received
    donor_notif = db_session.query(Notification).filter(
        Notification.user_id == donor.id,
        Notification.related_donation_id == donation.id
    ).first()
    assert donor_notif is not None
    assert "accepted" in donor_notif.message.lower()

    # Verify NO volunteer courier offers were created
    vol_offers = db_session.query(MatchOffer).filter(
        MatchOffer.donation_id == donation.id,
        MatchOffer.candidate_type == "volunteer"
    ).count()
    assert vol_offers == 0


# ==============================================================================
# TEST 2: Volunteer Assignment Strictly Prohibited in Self-Pickup Mode
# ==============================================================================
def test_02_volunteer_assignment_blocked_on_self_pickup_donation(db_session: Session, p4_environment: dict):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    ngo_a = p4_environment["ngo_a"]
    volunteer = p4_environment["volunteer"]

    donation = _create_fresh_donation(db_session, donor, "P4 Pasta Trays", quantity=25.0)
    donation.status = "accepted"
    donation.pickup_mode = "self_pickup"
    donation.assigned_ngo_id = ngo_a.id
    db_session.commit()

    # Attempt to assign volunteer courier via POST /api/volunteers/assignments
    headers = _get_auth_headers(volunteer)
    response = client.post(
        f"/api/volunteers/assignments?donation_id={donation.id}&volunteer_id={volunteer.id}",
        headers=headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "direct ngo self-pickup" in response.json()["detail"].lower()

    # Also test that accept_volunteer_assignment is blocked if an assignment existed
    dummy_assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=volunteer.id,
        status="assigned"
    )
    db_session.add(dummy_assignment)
    db_session.commit()
    db_session.refresh(dummy_assignment)

    accept_resp = client.post(
        f"/api/volunteers/assignments/{dummy_assignment.id}/accept",
        headers=headers
    )
    assert accept_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "direct ngo self-pickup" in accept_resp.json()["detail"].lower()


# ==============================================================================
# TEST 3: Mode Switch via /request-volunteer Triggers Wave 2 Courier Dispatch
# ==============================================================================
def test_03_request_volunteer_switches_mode_and_triggers_wave2_dispatch(db_session: Session, p4_environment: dict):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    ngo_a = p4_environment["ngo_a"]
    volunteer = p4_environment["volunteer"]

    donation = _create_fresh_donation(db_session, donor, "P4 Meals Switch", quantity=20.0)
    donation.status = "accepted"
    donation.pickup_mode = "self_pickup"
    donation.assigned_ngo_id = ngo_a.id
    db_session.commit()

    # NGO Alpha encounters vehicle trouble, requests volunteer support
    headers = _get_auth_headers(user_ngo_a)
    response = client.post(f"/api/donations/{donation.id}/request-volunteer", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["pickup_mode"] == "volunteer_dispatch"

    db_session.refresh(donation)
    assert donation.pickup_mode == "volunteer_dispatch"

    # Verify DonationHistory records switch
    history = db_session.query(DonationHistory).filter(
        DonationHistory.donation_id == donation.id,
        DonationHistory.remarks.contains("volunteer courier dispatch")
    ).first()
    assert history is not None

    # Now volunteer courier assignment is UNLOCKED
    vol_headers = _get_auth_headers(volunteer)
    assign_resp = client.post(
        f"/api/volunteers/assignments?donation_id={donation.id}&volunteer_id={volunteer.id}",
        headers=vol_headers
    )
    assert assign_resp.status_code == status.HTTP_200_OK, assign_resp.text
    assign_data = assign_resp.json()
    assert assign_data["status"] == "assigned"
    assert assign_data["volunteer_id"] == volunteer.id


# ==============================================================================
# TEST 4: Concurrency Safety — Two NGOs Attempting Simultaneous Acceptance
# ==============================================================================
def test_04_concurrency_two_ngos_simultaneous_acceptance_conflict_409(db_session: Session, p4_environment: dict):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    ngo_a = p4_environment["ngo_a"]
    user_ngo_b = p4_environment["user_ngo_b"]
    ngo_b = p4_environment["ngo_b"]

    donation = _create_fresh_donation(db_session, donor, "P4 Race Condition Batch", quantity=35.0)
    now = datetime.now(timezone.utc)

    # Offers to both NGOs
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        score=92.0,
        status="offered",
        wave_number=1,
        offered_at=now,
    )
    offer_b = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_b.id,
        candidate_type="ngo",
        score=88.0,
        status="offered",
        wave_number=1,
        offered_at=now,
    )
    db_session.add_all([offer_a, offer_b])
    db_session.commit()
    db_session.refresh(offer_a)
    db_session.refresh(offer_b)

    # NGO Alpha accepts first
    headers_a = _get_auth_headers(user_ngo_a)
    resp_a = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "self_pickup", "offer_id": offer_a.id},
        headers=headers_a
    )
    assert resp_a.status_code == status.HTTP_200_OK, resp_a.text

    # NGO Beta attempts to accept the exact same donation
    headers_b = _get_auth_headers(user_ngo_b)
    resp_b = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "self_pickup", "offer_id": offer_b.id},
        headers=headers_b
    )
    # Must be 409 Conflict
    assert resp_b.status_code == status.HTTP_409_CONFLICT
    assert "already been accepted" in resp_b.json()["detail"].lower() or "no longer active" in resp_b.json()["detail"].lower()

    # Verify donation remains safely assigned to NGO Alpha only
    db_session.refresh(donation)
    assert donation.assigned_ngo_id == ngo_a.id
    assert donation.pickup_mode == "self_pickup"


# ==============================================================================
# TEST 5: Uninvited NGO or Foreign Offer ID Rejected (403 Forbidden)
# ==============================================================================
def test_05_uninvited_ngo_or_foreign_offer_id_rejected(db_session: Session, p4_environment: dict):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    user_ngo_b = p4_environment["user_ngo_b"]

    donation = _create_fresh_donation(db_session, donor, "P4 Exclusive Offer", quantity=15.0)
    now = datetime.now(timezone.utc)

    # Offer dispatched exclusively to NGO Alpha
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        score=96.0,
        status="offered",
        wave_number=1,
        offered_at=now,
    )
    db_session.add(offer_a)
    db_session.commit()
    db_session.refresh(offer_a)

    headers_b = _get_auth_headers(user_ngo_b)

    # 1. NGO Beta attempts to accept without an offer (uninvited)
    resp_uninvited = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "self_pickup"},
        headers=headers_b
    )
    assert resp_uninvited.status_code == status.HTTP_403_FORBIDDEN
    assert "active offer to other shortlisted" in resp_uninvited.json()["detail"].lower()

    # 2. NGO Beta attempts to accept passing NGO Alpha's offer ID
    resp_tamper = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "self_pickup", "offer_id": offer_a.id},
        headers=headers_b
    )
    assert resp_tamper.status_code == status.HTTP_403_FORBIDDEN
    assert "does not belong to your organization" in resp_tamper.json()["detail"].lower()

    # 3. Passing a non-existent offer ID
    resp_nonexistent = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "self_pickup", "offer_id": 999999},
        headers=headers_b
    )
    assert resp_nonexistent.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# TEST 6: Direct NGO Self-Pickup OTP Verification, Delivery, and Distribution
# ==============================================================================
def test_06_direct_ngo_self_pickup_otp_verification_delivery_and_distribution(
    db_session: Session, p4_environment: dict
):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    ngo_a = p4_environment["ngo_a"]

    donation = _create_fresh_donation(db_session, donor, "P4 Complete Flow", quantity=30.0)
    now = datetime.now(timezone.utc)

    # Offer to NGO Alpha
    offer_a = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        score=99.0,
        status="offered",
        wave_number=1,
        offered_at=now,
    )
    db_session.add(offer_a)
    db_session.commit()
    db_session.refresh(offer_a)

    headers_ngo = _get_auth_headers(user_ngo_a)

    # 1. Accept with self_pickup
    accept_resp = client.post(
        f"/api/donations/{donation.id}/accept",
        json={"pickup_mode": "self_pickup", "offer_id": offer_a.id},
        headers=headers_ngo
    )
    assert accept_resp.status_code == status.HTTP_200_OK

    # 2. NGO driver arrives at donor location, verifies donor's OTP directly
    otp_resp = client.post(
        f"/api/donations/{donation.id}/pickup-otp/verify",
        json={"otp": donation.verification_otp},
        headers=headers_ngo
    )
    assert otp_resp.status_code == status.HTTP_200_OK, otp_resp.text
    assert otp_resp.json()["status"] == "collected"

    db_session.refresh(donation)
    assert donation.status == "collected"

    # 3. NGO delivers food to shelter facility
    deliver_resp = client.post(
        f"/api/donations/{donation.id}/deliver",
        headers=headers_ngo
    )
    assert deliver_resp.status_code == status.HTTP_200_OK, deliver_resp.text
    assert deliver_resp.json()["status"] == "delivered"

    db_session.refresh(donation)
    assert donation.status == "delivered"

    # 4. NGO records distribution to beneficiaries
    dist_payload = {
        "distributed_quantity": 30.0,
        "beneficiary_count": 30,
        "beneficiary_group": "Underprivileged children shelter",
        "remarks": "Distributed hot meals at lunch service",
    }
    dist_resp = client.post(
        f"/api/donations/{donation.id}/distribution",
        json=dist_payload,
        headers=headers_ngo
    )
    assert dist_resp.status_code == status.HTTP_200_OK, dist_resp.text
    dist_data = dist_resp.json()
    assert dist_data["distribution_status"] == "distributed"

    db_session.refresh(donation)
    assert donation.status == "completed"


# ==============================================================================
# TEST 7: NGO Convenience Endpoints (me/offers and me/self-pickups)
# ==============================================================================
def test_07_ngo_me_offers_and_me_self_pickups_endpoints(db_session: Session, p4_environment: dict):
    donor = p4_environment["donor"]
    user_ngo_a = p4_environment["user_ngo_a"]
    ngo_a = p4_environment["ngo_a"]

    donation = _create_fresh_donation(db_session, donor, "P4 Listed Self-Pickup", quantity=22.0)
    donation.status = "accepted"
    donation.pickup_mode = "self_pickup"
    donation.assigned_ngo_id = ngo_a.id

    now = datetime.now(timezone.utc)
    offer = MatchOffer(
        donation_id=donation.id,
        candidate_id=user_ngo_a.id,
        candidate_type="ngo",
        score=94.0,
        status="accepted",
        wave_number=1,
        offered_at=now - timedelta(minutes=5),
        responded_at=now,
    )
    db_session.add(offer)
    db_session.commit()

    headers_ngo = _get_auth_headers(user_ngo_a)

    # 1. Test GET /api/ngos/me/offers
    offers_resp = client.get("/api/ngos/me/offers", headers=headers_ngo)
    assert offers_resp.status_code == status.HTTP_200_OK, offers_resp.text
    offers = offers_resp.json()
    assert len(offers) >= 1
    assert any(o["donation_id"] == donation.id and o["status"] == "accepted" for o in offers)

    # 2. Test GET /api/ngos/me/self-pickups
    pickups_resp = client.get("/api/ngos/me/self-pickups", headers=headers_ngo)
    assert pickups_resp.status_code == status.HTTP_200_OK, pickups_resp.text
    pickups = pickups_resp.json()
    assert len(pickups) >= 1
    assert any(p["id"] == donation.id and p["pickup_mode"] == "self_pickup" for p in pickups)
