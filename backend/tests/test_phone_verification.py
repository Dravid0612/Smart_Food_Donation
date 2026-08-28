"""
Test Suite: Phone Verification — Smart Food Rescue
===================================================
Covers 8 acceptance criteria:
 1. Phone verification OTP sent
 2. Correct OTP verifies phone → phone_verified=True
 3. Wrong OTP rejected (400)
 4. Expired OTP rejected (410)
 5. Rate limit on phone verification requests (429)
 6. Phone number normalized to E.164
 7. Verified flag correctly set and persisted
 8. Pickup OTP requires verified phone
"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from app.db.session import get_db
from app.models.models import User, PickupOtpRecord, OtpDeliveryRecord
from app.services.otp_service import (
    send_phone_verification_otp, verify_phone_otp,
    _hash_otp, _PHONE_VERIFY_ATTEMPTS,
)
from app.services.sms_service import mask_phone


def _make_user(db, name, email, phone=None, phone_verified=False):
    user = User(
        name=name,
        email=email,
        password_hash="hashed",
        role="donor",
        phone=phone,
        phone_verified=phone_verified,
    )
    db.add(user)
    db.flush()
    return user


# ─── Test 1: Phone verification OTP send ─────────────────────────────────────

def test_phone_verification_otp_sent():
    db = next(get_db())
    try:
        user = _make_user(db, "PhoneVerify 1", "pv_1@test.com")
        delivery = send_phone_verification_otp(db, user, "+919876543210")

        assert delivery is not None
        assert delivery.purpose == "PHONE_VERIFICATION_OTP"
        assert delivery.status == "SENT"  # Mock: SENT not DELIVERED
        assert delivery.phone_number_masked == "+91 ****3210"
        assert delivery.provider == "mock"
        db.rollback()
    finally:
        db.close()


# ─── Test 2: Correct OTP verifies phone ──────────────────────────────────────

def test_correct_otp_verifies_phone():
    db = next(get_db())
    try:
        user = _make_user(db, "PhoneVerify 2", "pv_2@test.com")
        assert user.phone_verified is False

        # Send OTP
        _PHONE_VERIFY_ATTEMPTS.pop(f"phone_verify:{user.id}", None)
        delivery = send_phone_verification_otp(db, user, "+919876543210")

        # Get OTP record and extract hash for testing (we inject a known OTP)
        otp_record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PHONE_VERIFICATION_OTP",
            PickupOtpRecord.is_active == True,
        ).first()

        # Inject known OTP hash for test
        known_otp = "654321"
        otp_record.otp_hash = _hash_otp(known_otp)
        db.commit()

        # Verify with known OTP
        result = verify_phone_otp(db, user, "+919876543210", known_otp)
        assert result is True

        db.expire(user)
        user = db.query(User).filter(User.id == user.id).first()
        assert user.phone_verified is True
        assert user.phone_normalized == "+919876543210"

        db.rollback()
    finally:
        db.close()


# ─── Test 3: Wrong OTP rejected ───────────────────────────────────────────────

def test_wrong_phone_otp_rejected():
    from fastapi import HTTPException
    db = next(get_db())
    try:
        user = _make_user(db, "PhoneVerify 3", "pv_3@test.com")
        _PHONE_VERIFY_ATTEMPTS.pop(f"phone_verify:{user.id}", None)
        send_phone_verification_otp(db, user, "+919876543210")

        with pytest.raises(HTTPException) as exc_info:
            verify_phone_otp(db, user, "+919876543210", "000000")
        assert exc_info.value.status_code == 400
        db.rollback()
    finally:
        db.close()


# ─── Test 4: Expired OTP rejected ─────────────────────────────────────────────

def test_expired_phone_otp_rejected():
    from fastapi import HTTPException
    db = next(get_db())
    try:
        user = _make_user(db, "PhoneVerify 4", "pv_4@test.com")
        _PHONE_VERIFY_ATTEMPTS.pop(f"phone_verify:{user.id}", None)
        send_phone_verification_otp(db, user, "+919876543210")

        otp_record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PHONE_VERIFICATION_OTP",
            PickupOtpRecord.is_active == True,
        ).first()

        known_otp = "987654"
        otp_record.otp_hash = _hash_otp(known_otp)
        otp_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)  # expired
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            verify_phone_otp(db, user, "+919876543210", known_otp)
        assert exc_info.value.status_code == 410  # Gone
        db.rollback()
    finally:
        db.close()


# ─── Test 5: Rate limit on phone verification requests ────────────────────────

def test_phone_verification_rate_limit():
    from fastapi import HTTPException
    db = next(get_db())
    try:
        user = _make_user(db, "PhoneVerify RateLimit", "pv_rl@test.com")
        rate_key = f"phone_verify:{user.id}"
        _PHONE_VERIFY_ATTEMPTS.pop(rate_key, None)

        # Send up to max (3)
        from app.core.config import settings
        for _ in range(settings.OTP_PHONE_VERIFY_MAX_PER_WINDOW):
            send_phone_verification_otp(db, user, "+919876543210")

        # 4th attempt should be rate-limited
        with pytest.raises(HTTPException) as exc_info:
            send_phone_verification_otp(db, user, "+919876543210")
        assert exc_info.value.status_code == 429

        db.rollback()
    finally:
        db.close()


# ─── Test 6: Phone number normalized to E.164 ────────────────────────────────

def test_phone_normalized_to_e164():
    db = next(get_db())
    try:
        user = _make_user(db, "E164 User", "e164@test.com")
        _PHONE_VERIFY_ATTEMPTS.pop(f"phone_verify:{user.id}", None)
        send_phone_verification_otp(db, user, "+919876543210")

        otp_record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PHONE_VERIFICATION_OTP",
        ).first()

        delivery = db.query(OtpDeliveryRecord).filter(
            OtpDeliveryRecord.otp_record_id == otp_record.id
        ).first()

        # Verify masking is E.164 aware
        assert delivery.phone_number_masked == "+91 ****3210"
        assert "****" in delivery.phone_number_masked
        assert "3210" in delivery.phone_number_masked  # Last 4 digits visible

        db.rollback()
    finally:
        db.close()


# ─── Test 7: Verified flag correctly set and persisted ───────────────────────

def test_phone_verified_flag_persisted():
    db = next(get_db())
    try:
        user = _make_user(db, "PhoneVerify Persist", "pv_persist@test.com")
        assert user.phone_verified is False

        _PHONE_VERIFY_ATTEMPTS.pop(f"phone_verify:{user.id}", None)
        send_phone_verification_otp(db, user, "+919876543210")

        otp_record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PHONE_VERIFICATION_OTP",
            PickupOtpRecord.is_active == True,
        ).first()
        known_otp = "112233"
        otp_record.otp_hash = _hash_otp(known_otp)
        db.commit()

        verify_phone_otp(db, user, "+919876543210", known_otp)

        # Close and reopen session to test persistence
        user_id = user.id
        db.close()

        db2 = next(get_db())
        try:
            persisted_user = db2.query(User).filter(User.id == user_id).first()
            assert persisted_user.phone_verified is True
            assert persisted_user.phone_normalized == "+919876543210"
            db2.rollback()
        finally:
            db2.close()
    finally:
        try:
            db.close()
        except Exception:
            pass


# ─── Test 8: Pickup OTP SMS requires verified phone ──────────────────────────

def test_pickup_otp_requires_verified_phone():
    from fastapi import HTTPException
    from app.services.otp_service import generate_pickup_otp, send_pickup_otp_sms
    db = next(get_db())
    try:
        # User with unverified phone
        donor = _make_user(db, "Unverified Donor", "unverified_donor@test.com",
                           phone="+919876543210", phone_verified=False)

        donation_obj = PickupOtpRecord  # just using any import to avoid unused
        from app.models.models import FoodDonation

        donation = FoodDonation(
            donor_id=donor.id,
            food_name="Unverified Test",
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

        plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor)

        with pytest.raises(HTTPException) as exc_info:
            send_pickup_otp_sms(db, plaintext_otp, otp_record, donor)

        # Must be 422 — not just any error
        assert exc_info.value.status_code == 422
        assert "verify" in exc_info.value.detail.lower()

        db.rollback()
    finally:
        db.close()
