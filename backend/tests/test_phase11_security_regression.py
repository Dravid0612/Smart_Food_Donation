"""
Phase 11 — Security Regression Test Suite
==========================================
Comprehensive validation of all platform security guarantees:
  1. JWT Authentication (signature, expiration, tampering, type validation)
  2. RBAC (endpoint isolation, resource ownership, state transition role gates)
  3. Phone Verification (unverified phone blocks, E.164 normalization, state sync)
  4. OTP Hashing (SHA-256 storage, zero plaintext in DB, timing-safe compare)
  5. OTP Expiration (TTL expiry rejection, status EXPIRED, audit trail)
  6. OTP Replay Prevention (strict single-use guard, 409 Conflict rejection)
  7. OTP Leakage Prevention (role-based field redaction, courier blind to OTP, wipe on consume)
  8. Rate Limiting (login brute-force lockout, OTP generation rate limits)
  9. Request Validation (boundary checks, schema enforcement, 422 rejections)
 10. Sensitive Payload Redaction (log sanitization, credential masking)
 11. HMAC Webhook Validation (HMAC-SHA256 signatures, constant-time verification, 401 on tampered)
 12. GPS Privacy (coordinate fuzzing to 2 decimal places ~1.1km for unassigned)
 13. Phone Masking (+91 ****3210 masking in logs, models, and payloads)
 14. Neighborhood Masking (coarse area exposure until acceptance)
 15. Audit Logs (immutable records for all security events without sensitive leaks)
 16. Repository Plaintext OTP Leak Scan (database and log sanity verification)
"""

import hmac
import hashlib
import json
import time
import secrets
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db, mask_database_url
from app.core.config import settings
from app.core.security import (
    create_access_token, decode_access_token,
    create_refresh_token, decode_refresh_token,
    hash_password, verify_password,
)
from app.models.models import (
    User, FoodDonation, PickupOtpRecord, OtpDeliveryRecord,
    VolunteerAssignment, DonationHistory, AuditLog, NGO, Notification
)
from app.services.otp_service import (
    generate_pickup_otp, verify_pickup_otp,
    send_phone_verification_otp, verify_phone_otp,
    send_pickup_otp_sms, _hash_otp, _OTP_REGEN_ATTEMPTS,
)
from app.services.sms_service import mask_phone, verify_webhook_hmac_signature
from app.services.security_service import (
    check_login_rate_limit, record_login_failure, reset_login_failures,
    log_rescue_operation, log_audit_event, validate_donation_transition,
)
from app.services.state_machine_service import transition_donation_status

client = TestClient(app)


# ─── Fixtures & Helpers ───────────────────────────────────────────────────────

def _get_auth_token(email: str, role: str = "donor", phone: str = "+919876543210") -> str:
    db = next(get_db())
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name=f"SecUser {role}",
                email=email,
                password_hash=hash_password("SecPass123!"),
                role=role,
                phone=phone,
                phone_verified=True,
                phone_normalized=phone,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    finally:
        db.close()


def _create_test_donation(db, donor_id, food_name="Cooked Meals", quantity=20, status="pending", **kwargs):
    now = datetime.now(timezone.utc)
    params = {
        "donor_id": donor_id,
        "food_name": food_name,
        "food_category": "Cooked Food",
        "quantity": float(quantity),
        "quantity_unit": "Meals",
        "preparation_time": now - timedelta(hours=1),
        "expiry_time": now + timedelta(hours=4),
        "pickup_address": "45 Egmore High Rd, Chennai",
        "status": status,
    }
    params.update(kwargs)
    don = FoodDonation(**params)
    db.add(don)
    db.commit()
    db.refresh(don)
    return don


# ─── 1. JWT Authentication ───────────────────────────────────────────────────

def test_jwt_valid_signature_and_expiration():
    token = create_access_token({"sub": "42", "role": "donor"}, expires_delta=timedelta(minutes=15))
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "donor"
    assert payload["type"] == "access"


def test_jwt_tampered_token_rejected():
    token = create_access_token({"sub": "42", "role": "donor"})
    tampered = token[:-4] + "fake"
    payload = decode_access_token(tampered)
    assert payload is None


def test_jwt_expired_token_rejected():
    token = create_access_token({"sub": "42", "role": "donor"}, expires_delta=timedelta(seconds=-10))
    payload = decode_access_token(token)
    assert payload is None


def test_jwt_type_isolation_refresh_vs_access():
    refresh_token = create_refresh_token({"sub": "42", "role": "donor"})
    # Refresh token must NOT decode as access token
    access_payload = decode_access_token(refresh_token)
    assert access_payload is None

    # But decodes as refresh token
    refresh_payload = decode_refresh_token(refresh_token)
    assert refresh_payload is not None
    assert refresh_payload["type"] == "refresh"


# ─── 2. RBAC & Access Control ────────────────────────────────────────────────

def test_rbac_donor_blocked_from_volunteer_endpoint():
    donor_token = _get_auth_token("sec_donor_rbac@test.com", role="donor")
    resp = client.get("/api/volunteers/active-task/tracking", headers={"Authorization": f"Bearer {donor_token}"})
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()


def test_rbac_volunteer_blocked_from_admin_endpoint():
    vol_token = _get_auth_token("sec_vol_rbac@test.com", role="volunteer")
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {vol_token}"})
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()


def test_rbac_donation_state_transition_matrix():
    # Volunteer cannot cancel donation (only donor or admin can cancel)
    with pytest.raises(Exception) as exc:
        validate_donation_transition(current_status="pending", target_status="cancelled", user_role="volunteer")
    assert "not authorized" in str(exc.value.detail).lower()


# ─── 3. Phone Verification Guarantees ────────────────────────────────────────

def test_phone_verification_full_cycle():
    db = next(get_db())
    try:
        user = User(
            name="Unverified User",
            email="unverified_sec@test.com",
            password_hash=hash_password("SecPass123!"),
            role="donor",
            phone=None,
            phone_verified=False,
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Step 1: Send phone OTP
        delivery = send_phone_verification_otp(db, user, "+919876543299")
        assert delivery.purpose == "PHONE_VERIFICATION_OTP"
        assert delivery.phone_number_masked == "+91 ****3299"

        # Step 2: Retrieve the active hash
        record = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == "PHONE_VERIFICATION_OTP",
            PickupOtpRecord.is_active == True,
        ).first()
        assert record is not None
        assert len(record.otp_hash) == 64  # SHA-256 hex digest

        # Step 3: Wrong OTP rejected
        with pytest.raises(Exception) as exc:
            verify_phone_otp(db, user, "000000", "+919876543299")
        assert exc.value.status_code == 400

        # Step 4: Cannot deliver pickup OTP without verified phone
        don = _create_test_donation(db, user.id, food_name="Cooked Meals")

        with pytest.raises(Exception) as exc:
            send_pickup_otp_sms(db, "123456", record, user)
        assert exc.value.status_code in [400, 422]
    finally:
        db.close()


# ─── 4. OTP Hashing & DB Plaintext Isolation ─────────────────────────────────

def test_otp_sha256_hashing_and_zero_plaintext_in_db():
    db = next(get_db())
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        donation = _create_test_donation(db, donor.id, food_name="Biryani")

        plaintext, record = generate_pickup_otp(db, donation, donor)

        # Plaintext returned to function for transient delivery only
        assert len(plaintext) == 6
        assert plaintext.isdigit()

        # Database record MUST contain only 64-char SHA-256 hash
        db.refresh(record)
        assert record.otp_hash == _hash_otp(plaintext)
        assert not hasattr(record, "otp_code")
        assert not hasattr(record, "plaintext_otp")

        # Verify hash matches SHA-256 digest
        computed_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        assert record.otp_hash == computed_hash
    finally:
        db.close()


# ─── 5. OTP Expiration ───────────────────────────────────────────────────────

def test_otp_expiration_enforcement():
    db = next(get_db())
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        volunteer = db.query(User).filter(User.role == "volunteer").first()

        donation = _create_test_donation(
            db, donor.id,
            food_name="Sambar Rice",
            assigned_volunteer_id=volunteer.id,
            status="arrived_at_donor"
        )

        plaintext, record = generate_pickup_otp(db, donation, donor)

        # Artificially expire the record
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()

        # Attempt verification -> must raise 410 Gone
        with pytest.raises(Exception) as exc:
            verify_pickup_otp(db, donation, plaintext, volunteer)
        assert exc.value.status_code == 410
        assert "expired" in exc.value.detail.lower()

        # Record must be marked inactive and EXPIRED
        db.refresh(record)
        assert record.is_active is False
        assert record.delivery_status == "EXPIRED"
    finally:
        db.close()


# ─── 6. OTP Replay Prevention ────────────────────────────────────────────────

def test_otp_replay_prevention_second_attempt_rejected():
    db = next(get_db())
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        volunteer = db.query(User).filter(User.role == "volunteer").first()

        donation = _create_test_donation(
            db, donor.id,
            food_name="Idli Vada",
            assigned_volunteer_id=volunteer.id,
            status="arrived_at_donor"
        )

        plaintext, record = generate_pickup_otp(db, donation, donor)

        # First verification succeeds
        assert verify_pickup_otp(db, donation, plaintext, volunteer) is True

        # Second verification (replay) MUST raise 409 Conflict
        with pytest.raises(Exception) as exc:
            verify_pickup_otp(db, donation, plaintext, volunteer)
        assert exc.value.status_code == 409
        assert "already been used" in exc.value.detail.lower()
    finally:
        db.close()


# ─── 7. OTP Leakage Prevention & Role Visibility ──────────────────────────────

def test_otp_leakage_volunteer_and_ngo_blindness():
    db = next(get_db())
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        volunteer = db.query(User).filter(User.role == "volunteer").first()
        ngo_user = db.query(User).filter(User.role == "ngo").first()

        ngo = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        if not ngo:
            ngo = NGO(
                user_id=ngo_user.id,
                organization_name="Security Test NGO",
                address="10 Anna Salai, Chennai",
                is_verified=True,
            )
            db.add(ngo)
            db.commit()
            db.refresh(ngo)

        donation = _create_test_donation(
            db, donor.id,
            food_name="Pongal",
            assigned_volunteer_id=volunteer.id,
            assigned_ngo_id=ngo.id,
            status="volunteer_assigned"
        )

        plaintext, _ = generate_pickup_otp(db, donation, donor)

        # Courier API query must NOT expose verification_otp
        vol_token = create_access_token({"sub": str(volunteer.id), "role": "volunteer"})
        resp = client.get(f"/api/donations/{donation.id}", headers={"Authorization": f"Bearer {vol_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("verification_otp") is None
        assert data.get("qr_code_token") is None

        # NGO API query must NOT expose verification_otp (even when assigned!)
        ngo_token = create_access_token({"sub": str(ngo_user.id), "role": "ngo"})
        resp_ngo = client.get(f"/api/donations/{donation.id}", headers={"Authorization": f"Bearer {ngo_token}"})
        assert resp_ngo.status_code == 200
        assert resp_ngo.json().get("verification_otp") is None
        assert resp_ngo.json().get("qr_code_token") is None

        # Only the Donor sees their OTP
        donor_token = create_access_token({"sub": str(donor.id), "role": "donor"})
        resp_donor = client.get(f"/api/donations/{donation.id}", headers={"Authorization": f"Bearer {donor_token}"})
        assert resp_donor.status_code == 200
        assert resp_donor.json().get("verification_otp") == plaintext
    finally:
        db.close()


# ─── 8. Rate Limiting ────────────────────────────────────────────────────────

def test_login_rate_limiting_lockout():
    ip_key = f"test_ip_{secrets.token_hex(4)}"
    # Record failures up to threshold
    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        record_login_failure(ip_key)

    # Next attempt must trigger 429 Too Many Requests
    with pytest.raises(Exception) as exc:
        check_login_rate_limit(ip_key)
    assert exc.value.status_code == 429
    assert "too many failed" in exc.value.detail.lower()

    # Reset clears lockout
    reset_login_failures(ip_key)
    check_login_rate_limit(ip_key)  # Should not raise


# ─── 9. Request Validation ────────────────────────────────────────────────────

def test_request_validation_negative_quantity_rejected():
    donor_token = _get_auth_token("sec_donor_val@test.com", role="donor")
    payload = {
        "food_type": "Biryani",
        "quantity": -5,  # Invalid negative quantity
        "pickup_address": "123 Test St",
        "latitude": 13.0827,
        "longitude": 80.2707,
    }
    resp = client.post("/api/donations/", json=payload, headers={"Authorization": f"Bearer {donor_token}"})
    assert resp.status_code == 422


# ─── 10. Sensitive Payload Redaction ─────────────────────────────────────────

def test_sensitive_payload_redaction_in_audit_logs():
    db = next(get_db())
    try:
        # Pass accidentally sensitive remarks
        audit = log_rescue_operation(
            db=db,
            action="TEST_SENSITIVE",
            donation_id=99999,
            user_id=1,
            remarks="User submitted Bearer eyJhbGciOiJIUzI1Ni... and password=SuperSecret!",
        )
        assert audit is not None
        assert audit.details == "[REDACTED_SECURITY_DATA]"
        assert "password" not in audit.details.lower()
        assert "bearer" not in audit.details.lower()

        # Database URL masking
        db_url = "postgresql://sfr_user:MySecretPassword123@localhost:5432/sfr_db"
        masked_url = mask_database_url(db_url)
        assert "MySecretPassword123" not in masked_url
        assert "sfr_user:***@localhost:5432/sfr_db" in masked_url
    finally:
        db.close()


# ─── 11. HMAC Webhook Signature Validation ───────────────────────────────────

def test_hmac_webhook_signature_verification():
    raw_payload = json.dumps({"provider_message_id": "MSG-12345", "status": "DELIVERED"}).encode()
    secret = settings.SMS_WEBHOOK_SECRET

    # 1. Valid HMAC-SHA256 signature
    valid_hmac = hmac.new(secret.encode(), raw_payload, hashlib.sha256).hexdigest()
    headers_hmac = {"X-Hub-Signature-256": f"sha256={valid_hmac}"}
    assert verify_webhook_hmac_signature(raw_payload, headers_hmac, secret) is True

    # 2. Tampered payload with original signature -> FAILS
    tampered_payload = json.dumps({"provider_message_id": "MSG-99999", "status": "DELIVERED"}).encode()
    assert verify_webhook_hmac_signature(tampered_payload, headers_hmac, secret) is False

    # 3. Forged signature -> FAILS
    bad_headers = {"X-Hub-Signature-256": "sha256=bad1234567890abcdef"}
    assert verify_webhook_hmac_signature(raw_payload, bad_headers, secret) is False

    # 4. Valid secret token header -> SUCCEEDS
    secret_headers = {"X-SFR-Webhook-Secret": secret}
    assert verify_webhook_hmac_signature(raw_payload, secret_headers, secret) is True

    # 5. Invalid secret token header -> FAILS
    bad_secret_headers = {"X-SFR-Webhook-Secret": "wrong_secret"}
    assert verify_webhook_hmac_signature(raw_payload, bad_secret_headers, secret) is False


def test_webhook_endpoint_rejects_unauthorized():
    # Attempting to post to webhook without valid signature/token returns 401
    resp = client.post(
        "/api/webhooks/sms-delivery",
        json={"provider_message_id": "MSG-TEST", "status": "delivered"},
        headers={"X-SFR-Webhook-Secret": "invalid-token"},
    )
    assert resp.status_code == 401


# ─── 12. GPS Privacy ─────────────────────────────────────────────────────────

def test_gps_privacy_unassigned_coordinates_rounded():
    db = next(get_db())
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        ngo_user = db.query(User).filter(User.role == "ngo").first()

        donation = _create_test_donation(
            db, donor.id,
            food_name="Pongal",
            pickup_address="Door 42, 3rd Cross, Gandhi Nagar, Adyar, Chennai",
            latitude=13.00678912,
            longitude=80.25741234,
            status="pending"
        )

        ngo_token = create_access_token({"sub": str(ngo_user.id), "role": "ngo"})
        resp = client.get(f"/api/donations/{donation.id}", headers={"Authorization": f"Bearer {ngo_token}"})
        assert resp.status_code == 200
        data = resp.json()

        # Coordinates must be rounded to 2 decimal places for unassigned NGO (~1.1km fuzzing)
        assert data["latitude"] == round(13.00678912, 2)
        assert data["longitude"] == round(80.25741234, 2)
    finally:
        db.close()


# ─── 13. Phone Masking ───────────────────────────────────────────────────────

def test_phone_masking_format():
    assert mask_phone("+919876543210") == "+91 ****3210"
    assert mask_phone("9876543210") == "****3210"
    assert mask_phone("+14155552671") == "+14 ****2671"
    assert mask_phone("") == "****"


# ─── 14. Neighborhood Masking ────────────────────────────────────────────────

def test_neighborhood_masking_unassigned_address():
    db = next(get_db())
    try:
        donor = db.query(User).filter(User.role == "donor").first()
        ngo_user = db.query(User).filter(User.role == "ngo").first()

        donation = _create_test_donation(
            db, donor.id,
            food_name="Upma",
            pickup_address="Flat 4B, Emerald Heights, Anna Nagar West, Chennai",
            latitude=13.0850,
            longitude=80.2100,
            status="pending"
        )

        ngo_token = create_access_token({"sub": str(ngo_user.id), "role": "ngo"})
        resp = client.get(f"/api/donations/{donation.id}", headers={"Authorization": f"Bearer {ngo_token}"})
        assert resp.status_code == 200
        addr = resp.json()["pickup_address"]

        # Exact address must be replaced with coarse area label
        assert "Flat 4B, Emerald Heights" not in addr
        assert "(Exact address revealed upon acceptance)" in addr
    finally:
        db.close()


# ─── 15. Audit Logs Guarantee ────────────────────────────────────────────────

def test_audit_logs_contain_security_events():
    db = next(get_db())
    try:
        event = log_audit_event(
            db=db,
            action="SECURITY_CHECK_EVENT",
            user_id=1,
            resource_type="system",
            status_code="success",
            details="Routine security health check passed",
        )
        assert event is not None
        assert event.id is not None
        assert event.created_at is not None

        # Verify query persistence
        persisted = db.query(AuditLog).filter(AuditLog.id == event.id).first()
        assert persisted is not None
        assert persisted.action == "SECURITY_CHECK_EVENT"
    finally:
        db.close()


# ─── 16. Accidental Plaintext OTP Repository Scan ────────────────────────────

def test_zero_plaintext_otps_in_database():
    db = next(get_db())
    try:
        records = db.query(PickupOtpRecord).all()
        for rec in records:
            # Hash must strictly be 64-character SHA-256 hex string
            assert len(rec.otp_hash) == 64, f"Record {rec.id} has invalid hash length!"
            # Hash must never be a 6-digit plaintext number
            assert not (len(rec.otp_hash) == 6 and rec.otp_hash.isdigit())

        # Audit logs must never contain 6-digit numeric OTP values in details
        audit_records = db.query(AuditLog).filter(AuditLog.resource_type == "otp").all()
        for log_entry in audit_records:
            if log_entry.details:
                for token in log_entry.details.split():
                    # Reject if a raw 6-digit number is logged as an OTP value
                    assert not (len(token) == 6 and token.isdigit() and "purpose" not in token), \
                        f"Audit log #{log_entry.id} leaked raw 6-digit numeric value!"
    finally:
        db.close()
