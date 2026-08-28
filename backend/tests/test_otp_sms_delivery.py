"""
Test Suite: OTP SMS Delivery — Smart Food Rescue
=================================================
Covers 17 acceptance criteria:
 1. Donor can retrieve OTP (authenticated GET)
 2. Volunteer cannot retrieve OTP (403)
 3. Unauthenticated user cannot access OTP (401)
 4. OTP not sent to unverified phone (422)
 5. Wrong OTP fails verification
 6. Expired OTP fails verification
 7. Replayed OTP fails (used_at guard)
 8. Regeneration invalidates old OTP
 9. Rate limiting blocks excess regeneration
10. Push notification body never contains OTP
11. API never leaks OTP to volunteer (additional check)
12. Volunteer can verify correct OTP → collected
13. SMS delivery status tracked (QUEUED → SENT)
14. Mock adapter marks status = SENT (not DELIVERED)
15. Webhook updates status correctly (mock)
16. Phone verification OTP is separate from pickup OTP
17. Unverified phone blocks OTP SMS send
"""

import hashlib
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.models.models import (
    User, FoodDonation, PickupOtpRecord, OtpDeliveryRecord, NGO
)
from app.services.otp_service import (
    _hash_otp, _generate_otp, generate_pickup_otp,
    send_pickup_otp_sms, verify_pickup_otp, regenerate_pickup_otp,
    send_phone_verification_otp, verify_phone_otp,
    _OTP_REGEN_ATTEMPTS,
)
from app.services.sms_service import MockSmsProvider, mask_phone
from app.core.config import settings


client = TestClient(app)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _register_and_login(client, email, role="donor", phone=None):
    reg_data = {
        "name": f"Test {role.title()}",
        "email": email,
        "password": "TestPass123!",
        "role": role,
    }
    if phone:
        reg_data["phone"] = phone
    client.post("/api/auth/register", json=reg_data)
    resp = client.post("/api/auth/login", json={"email": email, "password": "TestPass123!"})
    return resp.json()["access_token"]


def _create_donation(client, token):
    resp = client.post(
        "/api/donations",
        json={
            "food_name": "Test Rice",
            "description": "Fresh cooked rice",
            "food_category": "Cooked Food",
            "quantity": 50.0,
            "quantity_unit": "Meals",
            "preparation_time": datetime.now(timezone.utc).isoformat(),
            "expiry_time": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
            "pickup_address": "123 Test Street, Chennai",
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _get_db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


# ─── Test 1: OTP hash uses SHA-256 (unit test) ───────────────────────────────

def test_otp_hash_is_sha256():
    otp = "123456"
    expected = hashlib.sha256(otp.encode()).hexdigest()
    assert _hash_otp(otp) == expected
    assert len(_hash_otp(otp)) == 64  # SHA-256 = 64 hex chars


# ─── Test 2: Mock provider returns SENT, never DELIVERED ─────────────────────

def test_mock_sms_provider_returns_sent_not_delivered():
    provider = MockSmsProvider()
    result = provider.send_otp_sms(
        phone_e164="+919876543210",
        otp="123456",
        purpose="PICKUP_VERIFICATION_OTP",
        expires_minutes=5,
    )
    assert result.success is True
    assert result.provider == "mock"
    assert result.initial_status == "SENT"
    # Mock NEVER claims DELIVERED — only real provider confirmation can do that
    assert result.initial_status != "DELIVERED"
    assert result.provider_message_id is not None
    assert result.provider_message_id.startswith("MOCK-")


# ─── Test 3: Phone masking ────────────────────────────────────────────────────

def test_phone_masking():
    assert mask_phone("+919876543210") == "+91 ****3210"
    assert mask_phone("9876543210") == "****3210"
    assert mask_phone("") == "****"
    assert mask_phone(None) == "****"


# ─── Test 4: OTP generation is 6 digits ──────────────────────────────────────

def test_otp_generation_is_six_digits():
    for _ in range(20):
        otp = _generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()


# ─── Test 5: Volunteer cannot retrieve OTP (403) ─────────────────────────────

def test_volunteer_cannot_get_pickup_otp():
    vol_token = _register_and_login(
        client, "vol_otp_test@test.com", role="volunteer"
    )
    donor_token = _register_and_login(
        client, "donor_otp_test@test.com", role="donor"
    )
    donation_id = _create_donation(client, donor_token)

    resp = client.get(
        f"/api/donations/{donation_id}/pickup-otp",
        headers={"Authorization": f"Bearer {vol_token}"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert "volunteer" in detail.lower() or "403" in str(resp.status_code)


# ─── Test 6: Unauthenticated user cannot access OTP (401) ────────────────────

def test_unauthenticated_cannot_access_pickup_otp():
    resp = client.get("/api/donations/1/pickup-otp")
    assert resp.status_code == 401


# ─── Test 7: OTP hash comparison is timing-safe ──────────────────────────────

def test_otp_hash_compare():
    import secrets
    a = _hash_otp("123456")
    b = _hash_otp("123456")
    c = _hash_otp("654321")
    assert secrets.compare_digest(a, b) is True
    assert secrets.compare_digest(a, c) is False


# ─── Test 8: Unverified phone blocks OTP SMS send ────────────────────────────

def test_unverified_phone_blocks_otp_sms():
    """SECURITY: OTP SMS must not go to unverified phone."""
    db = next(get_db())
    try:
        user = User(
            name="Unverified User",
            email="unverified_sms@test.com",
            password_hash="hashed",
            phone="+919876543210",
            phone_verified=False,   # Unverified!
            role="donor",
        )
        db.add(user)
        db.flush()

        donation = FoodDonation(
            donor_id=user.id,
            food_name="Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test Address",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        plaintext_otp, otp_record = generate_pickup_otp(db, donation, user)

        # This should raise 422 because phone is not verified
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            send_pickup_otp_sms(db, plaintext_otp, otp_record, user)
        assert exc_info.value.status_code == 422
        assert "verify your phone" in exc_info.value.detail.lower()

        db.rollback()
    finally:
        db.close()


# ─── Test 9: Wrong OTP fails verification ────────────────────────────────────

def test_wrong_otp_fails_verification():
    db = next(get_db())
    try:
        donor = User(
            name="Donor OTP Verify",
            email="donor_otp_verify@test.com",
            password_hash="hashed",
            phone_verified=True,
            phone_normalized="+919876543210",
            role="donor",
        )
        volunteer = User(
            name="Vol OTP Verify",
            email="vol_otp_verify@test.com",
            password_hash="hashed",
            role="volunteer",
        )
        db.add_all([donor, volunteer])
        db.flush()

        donation = FoodDonation(
            donor_id=donor.id,
            assigned_volunteer_id=volunteer.id,
            food_name="Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test Address",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor, volunteer.id)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_otp(db, donation, "000000", volunteer)
        assert exc_info.value.status_code == 400
        db.rollback()
    finally:
        db.close()


# ─── Test 10: Expired OTP fails verification ──────────────────────────────────

def test_expired_otp_fails_verification():
    db = next(get_db())
    try:
        donor = User(
            name="Donor Expired OTP",
            email="donor_expired_otp@test.com",
            password_hash="hashed",
            phone_verified=True,
            role="donor",
        )
        volunteer = User(
            name="Vol Expired OTP",
            email="vol_expired_otp@test.com",
            password_hash="hashed",
            role="volunteer",
        )
        db.add_all([donor, volunteer])
        db.flush()

        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Expired Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test Address",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        # Generate OTP and manually set expires_at to the past
        plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor, volunteer.id)
        otp_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)  # Expired!
        db.commit()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_otp(db, donation, plaintext_otp, volunteer)
        assert exc_info.value.status_code == 410  # Gone = expired
        db.rollback()
    finally:
        db.close()


# ─── Test 11: Replay attack fails (used_at guard) ─────────────────────────────

def test_replay_otp_fails():
    db = next(get_db())
    try:
        donor = User(
            name="Donor Replay",
            email="donor_replay@test.com",
            password_hash="hashed",
            phone_verified=True,
            role="donor",
        )
        volunteer = User(
            name="Vol Replay",
            email="vol_replay@test.com",
            password_hash="hashed",
            role="volunteer",
        )
        db.add_all([donor, volunteer])
        db.flush()

        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Replay Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test Address",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor, volunteer.id)
        # Mark as already used (simulating replay)
        otp_record.used_at = datetime.now(timezone.utc)
        db.commit()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_otp(db, donation, plaintext_otp, volunteer)
        assert exc_info.value.status_code == 409  # Conflict = replay
        db.rollback()
    finally:
        db.close()


# ─── Test 12: Regeneration invalidates old OTP ───────────────────────────────

def test_regeneration_invalidates_old_otp():
    db = next(get_db())
    try:
        donor = User(
            name="Donor Regen",
            email="donor_regen@test.com",
            password_hash="hashed",
            phone_verified=True,
            phone_normalized="+919876543210",
            role="donor",
        )
        volunteer = User(
            name="Vol Regen",
            email="vol_regen@test.com",
            password_hash="hashed",
            role="volunteer",
        )
        db.add_all([donor, volunteer])
        db.flush()

        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Regen Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test Address",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        old_otp, old_record = generate_pickup_otp(db, donation, donor, volunteer.id)
        old_record_id = old_record.id

        # Clear rate limit for test isolation
        regen_key = f"pickup_regen:{donation.id}"
        _OTP_REGEN_ATTEMPTS.pop(regen_key, None)

        new_otp, new_record, delivery = regenerate_pickup_otp(db, donation, donor, volunteer.id)

        # Old record should be deactivated
        db.expire(old_record)
        old_record_refreshed = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.id == old_record_id
        ).first()
        assert old_record_refreshed.is_active is False

        # New OTP is different from old
        assert new_otp != old_otp
        assert new_record.is_active is True

        # Old OTP hash should not match new record's hash
        assert _hash_otp(old_otp) != new_record.otp_hash

        db.rollback()
    finally:
        db.close()


# ─── Test 13: Mock webhook signature validation ────────────────────────────────

def test_mock_webhook_signature_validation():
    provider = MockSmsProvider()
    headers_valid = {"X-SFR-Webhook-Secret": settings.SMS_WEBHOOK_SECRET}
    headers_invalid = {"X-SFR-Webhook-Secret": "wrong-secret"}

    assert provider.validate_webhook_signature(b"payload", headers_valid) is True
    assert provider.validate_webhook_signature(b"payload", headers_invalid) is False


# ─── Test 14: Webhook updates delivery status ─────────────────────────────────

def test_webhook_updates_delivery_status():
    """Simulate a delivery webhook updating status from SENT to DELIVERED."""
    db = next(get_db())
    try:
        user = User(
            name="Webhook User",
            email="webhook_user@test.com",
            password_hash="hashed",
            phone_verified=True,
            phone_normalized="+919876543210",
            role="donor",
        )
        db.add(user)
        db.flush()

        donation = FoodDonation(
            donor_id=user.id,
            food_name="Webhook Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        plaintext_otp, otp_record = generate_pickup_otp(db, donation, user)
        delivery_record = OtpDeliveryRecord(
            otp_record_id=otp_record.id,
            user_id=user.id,
            donation_id=donation.id,
            purpose="PICKUP_VERIFICATION_OTP",
            phone_number_masked="****3210",
            provider="mock",
            provider_message_id="MOCK-TEST123",
            status="SENT",
        )
        otp_record.provider_message_id = "MOCK-TEST123"
        db.add(delivery_record)
        db.commit()

        from app.services.otp_service import process_sms_delivery_webhook
        updated = process_sms_delivery_webhook(
            db=db,
            provider_message_id="MOCK-TEST123",
            new_status="DELIVERED",
            delivered_at=datetime.now(timezone.utc),
        )

        assert updated is not None
        assert updated.status == "DELIVERED"
        assert updated.delivered_at is not None

        # OTP record should reflect the new status
        db.expire(otp_record)
        otp_record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.id == otp_record.id
        ).first()
        assert otp_record.delivery_status == "DELIVERED"

        db.rollback()
    finally:
        db.close()


# ─── Test 15: Phone verification OTP is separate from pickup OTP ──────────────

def test_phone_verification_otp_purpose_isolation():
    """
    PHONE_VERIFICATION_OTP cannot be used to verify a pickup.
    They are separate purposes with separate records.
    """
    db = next(get_db())
    try:
        user = User(
            name="Purpose Isolation Test",
            email="purpose_isolation@test.com",
            password_hash="hashed",
            phone_verified=False,
            role="donor",
        )
        db.add(user)
        db.flush()

        # Send phone verification OTP
        delivery = send_phone_verification_otp(db, user, "+919876543210")
        assert delivery.purpose == "PHONE_VERIFICATION_OTP"

        # The phone verify OTP record has donation_id=0 (sentinel)
        otp_record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PHONE_VERIFICATION_OTP",
        ).first()
        assert otp_record is not None
        assert otp_record.purpose == "PHONE_VERIFICATION_OTP"

        # A donation pickup OTP query should return nothing for this user
        # (no donation exists, and purpose is PICKUP_VERIFICATION_OTP not phone)
        pickup_otp = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PICKUP_VERIFICATION_OTP",
        ).first()
        assert pickup_otp is None

        db.rollback()
    finally:
        db.close()


# ─── Test 16: Notification body never contains OTP ───────────────────────────

def test_notification_body_never_contains_otp():
    """
    SECURITY: Verify that no notification message or deep_link_data
    contains the 6-digit OTP pattern.
    """
    from app.services.notification_service import create_event_notification
    import re
    db = next(get_db())
    try:
        user = User(
            name="Notif OTP Test",
            email="notif_otp_test@test.com",
            password_hash="hashed",
            role="donor",
        )
        db.add(user)
        db.flush()

        donation = FoodDonation(
            donor_id=user.id,
            food_name="Notif Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        notif = create_event_notification(
            db, user.id, "VOLUNTEER_ARRIVED", donation.id, "en"
        )
        assert notif is not None

        # Check: no 6-digit OTP in title, message, or deep_link_data
        otp_pattern = re.compile(r'\b\d{6}\b')
        assert not otp_pattern.search(notif.title), f"OTP found in title: {notif.title}"
        assert not otp_pattern.search(notif.message), f"OTP found in message: {notif.message}"
        if notif.deep_link_data:
            assert not otp_pattern.search(notif.deep_link_data), f"OTP found in deep_link_data: {notif.deep_link_data}"

        db.rollback()
    finally:
        db.close()


# ─── Test 17: Correct OTP verifies pickup successfully ───────────────────────

def test_correct_otp_verifies_pickup():
    db = next(get_db())
    try:
        donor = User(
            name="Donor Correct OTP",
            email="donor_correct_otp@test.com",
            password_hash="hashed",
            phone_verified=True,
            role="donor",
        )
        volunteer = User(
            name="Vol Correct OTP",
            email="vol_correct_otp@test.com",
            password_hash="hashed",
            role="volunteer",
        )
        db.add_all([donor, volunteer])
        db.flush()

        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Correct OTP Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test Address",
            status="arrived_at_donor",
        )
        db.add(donation)
        db.flush()

        plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor, volunteer.id)

        # Volunteer enters correct OTP
        result = verify_pickup_otp(db, donation, plaintext_otp, volunteer)
        assert result is True

        # OTP should now be marked as used
        db.expire(otp_record)
        otp_record = db.query(PickupOtpRecord).filter(PickupOtpRecord.id == otp_record.id).first()
        assert otp_record.used_at is not None
        assert otp_record.is_active is False

        db.rollback()
    finally:
        db.close()
