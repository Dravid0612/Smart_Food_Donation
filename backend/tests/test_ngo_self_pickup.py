import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.models import FoodDonation, NGO, User, PickupOtpRecord
from app.core.security import create_access_token
from app.services.otp_service import generate_pickup_otp

client = TestClient(app)

def _get_auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}

def test_ngo_accept_with_self_pickup_and_switch_to_volunteer():
    db = SessionLocal()
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        ngo_user = db.query(User).filter(User.role == "ngo").first()
        ngo = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        ngo.is_verified = True
        ngo.current_capacity = 200
        db.commit()

        now = datetime.now(timezone.utc)
        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Temple Pongal Surplus",
            food_category="Cooked Food",
            quantity=60.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            pickup_address="Malleswaram, Bangalore",
            latitude=13.0031,
            longitude=77.5643,
            status="pending",
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        # 1. NGO accepts with self_pickup mode
        headers_ngo = _get_auth_headers(ngo_user)
        resp = client.post(
            f"/api/donations/{donation.id}/accept",
            headers=headers_ngo,
            json={"pickup_mode": "self_pickup", "remarks": "Our NGO van is nearby"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["pickup_mode"] == "self_pickup"
        assert data["assigned_ngo_id"] == ngo.id

        # 2. NGO switches from self_pickup to volunteer_dispatch
        switch_resp = client.post(
            f"/api/donations/{donation.id}/request-volunteer",
            headers=headers_ngo
        )
        assert switch_resp.status_code == 200, switch_resp.text
        switch_data = switch_resp.json()
        assert switch_data["pickup_mode"] == "volunteer_dispatch"

    finally:
        db.close()


def test_ngo_self_pickup_direct_otp_verification():
    db = SessionLocal()
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        ngo_user = db.query(User).filter(User.role == "ngo").first()
        ngo = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        ngo.is_verified = True
        ngo.current_capacity = 200
        donor.phone_verified = True
        db.commit()

        now = datetime.now(timezone.utc)
        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Buffet Rice & Sambar",
            food_category="Cooked Food",
            quantity=40.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            pickup_address="Koramangala, Bangalore",
            latitude=12.9352,
            longitude=77.6245,
            status="pending",
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        # NGO accepts with self_pickup
        headers_ngo = _get_auth_headers(ngo_user)
        accept_resp = client.post(
            f"/api/donations/{donation.id}/accept",
            headers=headers_ngo,
            json={"pickup_mode": "self_pickup"}
        )
        assert accept_resp.status_code == 200

        # Generate OTP
        plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor)
        db.commit()

        # Receiving NGO enters the OTP at donor pickup location
        verify_resp = client.post(
            f"/api/donations/{donation.id}/pickup-otp/verify",
            headers=headers_ngo,
            json={"otp": plaintext_otp}
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "collected"

        # Check DB status
        db.refresh(donation)
        assert donation.status == "collected"

    finally:
        db.close()
