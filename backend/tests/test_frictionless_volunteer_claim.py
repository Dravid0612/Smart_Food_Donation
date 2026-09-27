import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import secrets

from app.main import app
from app.db.session import SessionLocal
from app.models.models import (
    FoodDonation, User, VolunteerAssignment, RescueClaimToken, DonationHistory, AuditLog, PickupOtpRecord
)
from app.core.security import create_access_token, hash_password
from app.services.otp_service import generate_pickup_otp

client = TestClient(app)

def _get_auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role, "name": user.name})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_setup():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        donor = db.query(User).filter(User.role == "donor").first()
        if not donor:
            donor = User(
                name="Test Donor Kitchen",
                email=f"donor_{secrets.token_hex(4)}@test.com",
                password_hash=hash_password("pass123"),
                phone="+919845122301",
                phone_normalized="+919845122301",
                role="donor",
                address="142, 5th Block, Koramangala, Bangalore",
                latitude=12.9348,
                longitude=77.6235,
                is_active=True
            )
            db.add(donor)
            db.commit()
            db.refresh(donor)

        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Paneer Biryani & Dal Makhani",
            food_category="Cooked Food",
            quantity=25.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(minutes=45),
            expiry_time=now + timedelta(hours=3),
            pickup_address="142, 5th Block, 80 Feet Road, Koramangala, Bangalore",
            latitude=12.9348,
            longitude=77.6235,
            status="pending",
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        yield {"db": db, "donor": donor, "donation": donation}
    finally:
        db.close()


def test_generate_claim_token(test_setup):
    db = test_setup["db"]
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    headers = _get_auth_headers(donor)
    resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "claim_token" in data
    assert data["claim_url"] == f"/claim/{data['claim_token']}"
    assert data["donation_id"] == donation.id
    assert data["remaining_minutes"] > 0
    assert data["urgency_level"] in ["FRESH", "APPROACHING", "URGENT", "CRITICAL"]

    # Verify token stored in DB
    claim_record = db.query(RescueClaimToken).filter(RescueClaimToken.token == data["claim_token"]).first()
    assert claim_record is not None
    assert claim_record.is_active is True
    assert claim_record.donation_id == donation.id


def test_public_claim_preview_privacy(test_setup):
    db = test_setup["db"]
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    # Generate claim token
    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    # Call public preview without any auth headers
    resp = client.get(f"/api/volunteers/claims/{claim_token}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["food_name"] == donation.food_name
    assert data["quantity"] == 25.0
    assert data["quantity_unit"] == "Meals"
    assert data["remaining_minutes"] > 0
    # Must expose coarse neighborhood, NOT exact door address
    assert "area" in data["pickup_neighborhood"] or "Koramangala" in data["pickup_neighborhood"]
    assert "142, 5th Block" not in data["pickup_neighborhood"]
    # Coordinates must be rounded
    if data["approx_latitude"]:
        assert str(data["approx_latitude"]).split(".")[1].__len__() <= 3

    # Security check: MUST NOT expose donor phone or OTP
    assert "donor_phone" not in data
    assert "verification_otp" not in data
    assert "otp" not in data
    assert donor.phone not in str(data)


def test_frictionless_claim_acceptance_success(test_setup):
    db = test_setup["db"]
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    # First-time volunteer accepts with minimal name & phone
    accept_payload = {
        "name": "Arun Kumar",
        "phone": "+919876001234",
        "vehicle_type": "bike",
        "carrying_capacity": 50,
        "current_lat": 12.9360,
        "current_lon": 77.6230
    }
    resp = client.post(f"/api/volunteers/claims/{claim_token}/accept", json=accept_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["status"] == "volunteer_assigned"
    # Exact pickup address revealed upon acceptance
    assert data["pickup_address"] == donation.pickup_address
    assert data["user"]["name"] == "Arun Kumar"
    assert data["user"]["role"] == "volunteer"

    # Verify donation state in DB
    db.refresh(donation)
    assert donation.status == "volunteer_assigned"
    assert donation.assigned_volunteer_id == data["user"]["id"]

    # Verify assignment record in DB
    assignment = db.query(VolunteerAssignment).filter(VolunteerAssignment.id == data["assignment_id"]).first()
    assert assignment is not None
    assert assignment.status == "assigned"
    assert assignment.volunteer_id == data["user"]["id"]

    # Verify claim token is invalidated
    token_rec = db.query(RescueClaimToken).filter(RescueClaimToken.token == claim_token).first()
    assert token_rec.is_active is False
    assert token_rec.claimed_at is not None
    assert token_rec.claimed_by_user_id == data["user"]["id"]

    # Verify DonationHistory audit entry
    history = db.query(DonationHistory).filter(DonationHistory.donation_id == donation.id).order_by(DonationHistory.id.desc()).first()
    assert history is not None
    assert history.new_status == "volunteer_assigned"
    assert "Arun Kumar" in history.remarks

    # Verify AuditLog security entry
    audit = db.query(AuditLog).filter(AuditLog.resource_id == donation.id, AuditLog.action == "volunteer_claim_accepted").first()
    assert audit is not None
    assert audit.status == "success"


def test_token_invalidation_prevents_duplicate_claims(test_setup):
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    # Volunteer A accepts
    resp_a = client.post(f"/api/volunteers/claims/{claim_token}/accept", json={
        "name": "Volunteer Alpha",
        "phone": "+919811112222",
        "carrying_capacity": 50
    })
    assert resp_a.status_code == 200, resp_a.text

    # Volunteer B attempts to accept with the same token
    resp_b = client.post(f"/api/volunteers/claims/{claim_token}/accept", json={
        "name": "Volunteer Beta",
        "phone": "+919833334444",
        "carrying_capacity": 50
    })
    # Must fail with 409 Conflict
    assert resp_b.status_code == 409
    assert "already been claimed" in resp_b.json()["detail"].lower()


def test_claim_rejected_when_capacity_insufficient(test_setup):
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    # Donation has 25 meals; volunteer specifies capacity of 10 meals
    resp = client.post(f"/api/volunteers/claims/{claim_token}/accept", json={
        "name": "Volunteer SmallCapacity",
        "phone": "+919855556666",
        "carrying_capacity": 10
    })
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_invalid_and_expired_claim_tokens(test_setup):
    db = test_setup["db"]
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    # 1. Non-existent token -> 404
    resp_fake = client.get("/api/volunteers/claims/non_existent_token_12345")
    assert resp_fake.status_code == 404

    # 2. Expired token -> 410 Gone
    expired_token_str = "expired_token_" + secrets.token_hex(8)
    now = datetime.now(timezone.utc)
    expired_claim = RescueClaimToken(
        donation_id=donation.id,
        token=expired_token_str,
        created_at=now - timedelta(hours=2),
        expires_at=now - timedelta(minutes=10),
        is_active=True
    )
    db.add(expired_claim)
    db.commit()

    resp_exp_get = client.get(f"/api/volunteers/claims/{expired_token_str}")
    assert resp_exp_get.status_code == 410
    assert "expired" in resp_exp_get.json()["detail"].lower()

    resp_exp_post = client.post(f"/api/volunteers/claims/{expired_token_str}/accept", json={
        "name": "Volunteer Late",
        "phone": "+919877778888"
    })
    assert resp_exp_post.status_code == 410


def test_claim_fails_if_donation_cancelled_or_expired(test_setup):
    db = test_setup["db"]
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    # Cancel donation
    donation.status = "cancelled"
    db.commit()

    resp = client.get(f"/api/volunteers/claims/{claim_token}")
    assert resp.status_code == 409
    assert "no longer available" in resp.json()["detail"].lower()

    resp_accept = client.post(f"/api/volunteers/claims/{claim_token}/accept", json={
        "name": "Volunteer Test",
        "phone": "+919899990000"
    })
    assert resp_accept.status_code == 409


def test_optional_volunteer_account_upgrade(test_setup):
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    # 1. Volunteer accepts claim
    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    claim_resp = client.post(f"/api/volunteers/claims/{claim_token}/accept", json={
        "name": "Kiran Rao",
        "phone": "+919812345678",
        "carrying_capacity": 60
    })
    assert claim_resp.status_code == 200
    token = claim_resp.json()["access_token"]
    vol_headers = {"Authorization": f"Bearer {token}"}

    # 2. Upgrade account with email and permanent password
    new_email = f"kiran.rao.{secrets.token_hex(3)}@gmail.com"
    upgrade_resp = client.post(
        "/api/volunteers/upgrade-account",
        headers=vol_headers,
        json={
            "email": new_email,
            "password": "SecurePassword123!",
            "preferred_language": "ta"
        }
    )
    assert upgrade_resp.status_code == 200, upgrade_resp.text
    upgraded_data = upgrade_resp.json()
    assert upgraded_data["email"] == new_email
    assert upgraded_data["preferred_language"] == "ta"

    # 3. Verify user can now log in with the new credentials
    login_resp = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": "SecurePassword123!"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_security_claim_token_isolation_and_no_otp_leak(test_setup):
    donor = test_setup["donor"]
    donation = test_setup["donation"]

    # Generate authoritative OTP on donation
    otp_data = generate_pickup_otp(test_setup["db"], donation, donor)
    secret_otp = otp_data[0]

    headers = _get_auth_headers(donor)
    token_resp = client.post(f"/api/volunteers/donations/{donation.id}/claim-token", headers=headers)
    claim_token = token_resp.json()["claim_token"]

    # 1. Preview must NEVER contain OTP
    preview_resp = client.get(f"/api/volunteers/claims/{claim_token}")
    assert secret_otp not in preview_resp.text

    # 2. Claim accept response must NEVER contain OTP
    accept_resp = client.post(f"/api/volunteers/claims/{claim_token}/accept", json={
        "name": "Secret Volunteer",
        "phone": "+919822223333"
    })
    assert secret_otp not in accept_resp.text
