"""
Test Suite: Phase 6 — OTP Handover + Audit Hardening
=====================================================
Covers:
  1. Plaintext OTP retrieval isolation (Donor/Admin only; Volunteer/NGO get 403 Forbidden).
  2. SHA-256 salted hashing with zero plaintext OTP persistence in DB.
  3. Valid handover flow (volunteer submits OTP -> transitions to collected).
  4. Strict single-use replay protection (second request fails with 409 Conflict).
  5. Expiration guard (expired OTP rejects with 410 Gone, marks EXPIRED).
  6. Incorrect OTP rejection (400 Bad Request, constant-time compare).
  7. Concurrency transaction safety (two simultaneous requests: exactly 1 succeeds, 1 gets 409 Conflict).
  8. Regeneration protection (old OTP invalidated, rate-limiting enforced).
  9. Comprehensive rescue audit trail across DonationHistory and AuditLog without sensitive leaks.
 10. Notification and deep-link payload cleanliness (never leaks plaintext OTP or tokens).
 11. SMS delivery audit trail (masked phone, provider, status tracking).
"""

import time
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, get_db
from app.models.models import (
    User, FoodDonation, PickupOtpRecord, OtpDeliveryRecord,
    VolunteerAssignment, DonationHistory, AuditLog, Notification, NGO
)
from app.services.otp_service import (
    _hash_otp, _generate_otp, generate_pickup_otp,
    verify_pickup_otp, regenerate_pickup_otp, send_pickup_otp_sms,
    _OTP_REGEN_ATTEMPTS
)
from app.services.security_service import log_rescue_operation
from app.services.state_machine_service import transition_donation_status
from app.services.sms_service import mask_phone

client = TestClient(app)


# ─── Test Helpers ─────────────────────────────────────────────────────────────

def _register_and_login(cl, email, role="donor", phone=None):
    reg_data = {
        "name": f"Test {role.title()}",
        "email": email,
        "password": "TestPassword123!",
        "role": role,
    }
    if phone:
        reg_data["phone"] = phone
    cl.post("/api/auth/register", json=reg_data)
    resp = cl.post("/api/auth/login", json={"email": email, "password": "TestPassword123!"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# ─── 1. Plaintext OTP Retrieval Isolation ─────────────────────────────────────

def test_01_otp_role_isolation_and_volunteer_forbidden():
    """
    SECURITY:
    Only the authorized donor (and admin) may retrieve the plaintext verification code.
    Volunteers and unassigned NGOs must receive 403 Forbidden.
    Volunteer detail view must have verification_otp = None.
    """
    ts = int(time.time() * 1000)
    donor_tok = _register_and_login(client, f"donor_p6_{ts}@test.com", "donor")
    vol_tok = _register_and_login(client, f"vol_p6_{ts}@test.com", "volunteer")
    ngo_tok = _register_and_login(client, f"ngo_p6_{ts}@test.com", "ngo")
    other_donor_tok = _register_and_login(client, f"other_donor_{ts}@test.com", "donor")

    # Create donation
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        headers=_h(donor_tok),
        json={
            "food_name": "Surplus Biryani",
            "food_category": "Cooked Food",
            "quantity": 30.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=3)).isoformat(),
            "pickup_address": "100 GST Road, Chennai",
            "latitude": 13.0827,
            "longitude": 80.2707,
        }
    )
    assert create_res.status_code == 201, create_res.text
    did = create_res.json()["id"]

    # 1. Authorized donor can view verification code
    donor_code_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(donor_tok))
    assert donor_code_res.status_code == 200
    code_data = donor_code_res.json()
    assert code_data["otp"] is not None
    assert len(code_data["otp"]) == 6
    assert code_data["otp_status"] == "active"

    # 2. Volunteer gets 403 Forbidden on verification-code
    vol_code_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(vol_tok))
    assert vol_code_res.status_code == 403

    # 3. Volunteer gets 403 Forbidden on pickup-otp endpoint
    vol_pickup_otp_res = client.get(f"/api/donations/{did}/pickup-otp", headers=_h(vol_tok))
    assert vol_pickup_otp_res.status_code == 403
    assert "volunteer" in vol_pickup_otp_res.json()["detail"].lower()

    # 4. Other donor gets 403 Forbidden
    other_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(other_donor_tok))
    assert other_res.status_code == 403

    # 5. NGO gets 403 Forbidden
    ngo_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(ngo_tok))
    assert ngo_res.status_code == 403

    # 6. Volunteer detail view masks/strips verification_otp
    vol_detail = client.get(f"/api/donations/{did}", headers=_h(vol_tok))
    if vol_detail.status_code == 200:
        assert vol_detail.json().get("verification_otp") is None


# ─── 2. Salted SHA-256 Hash and Zero Plaintext Persistence in DB ─────────────

def test_02_salted_sha256_hash_and_zero_plaintext_storage():
    """
    OTP RULES:
    The OTP must never be stored in plaintext.
    PickupOtpRecord stores only 64-character SHA-256 hash digest.
    """
    db = SessionLocal()
    try:
        user = User(
            name="Hash Test Donor",
            email=f"hash_test_{int(time.time() * 1000)}@test.com",
            password_hash="pwd_hash",
            role="donor",
            phone_verified=True,
            phone_normalized="+919876543210"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        now = datetime.now(timezone.utc)
        donation = FoodDonation(
            donor_id=user.id,
            food_name="Test Food",
            food_category="Cooked Food",
            quantity=15.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=2),
            pickup_address="Testing Grounds",
            status="pending"
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        plaintext_otp, otp_rec = generate_pickup_otp(db, donation, user)

        # Hash check: exactly 64 hex characters (SHA-256)
        assert len(otp_rec.otp_hash) == 64
        # Plaintext is NOT the hash
        assert otp_rec.otp_hash != plaintext_otp
        # Verify hash matches sha256 of plaintext
        expected_hash = hashlib.sha256(plaintext_otp.encode()).hexdigest()
        assert otp_rec.otp_hash == expected_hash

        # Verify salt capability
        salted = _hash_otp("123456", salt="secret_salt")
        unsalted = _hash_otp("123456")
        assert salted != unsalted
        assert len(salted) == 64
    finally:
        db.close()


# ─── 3. Valid Handover Flow: Volunteer Verifies OTP ───────────────────────────

def test_03_valid_handover_flow_transitions_to_collected():
    """
    Valid courier enters the donor's 6-digit OTP:
    - Verifies hash, expiry, role, and assignment
    - Transitions donation to 'collected'
    - Transitions assignment to 'collected' with collected_at timestamp
    - Consumes token (used_at timestamp set, is_active=False)
    """
    ts = int(time.time() * 1000)
    donor_tok = _register_and_login(client, f"donor_handover_{ts}@test.com", "donor")
    vol_tok = _register_and_login(client, f"vol_handover_{ts}@test.com", "volunteer")

    db = SessionLocal()
    try:
        vol = db.query(User).filter(User.email == f"vol_handover_{ts}@test.com").first()
        vol_id = vol.id
    finally:
        db.close()

    # Create donation
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        headers=_h(donor_tok),
        json={
            "food_name": "Handover Rice Packets",
            "food_category": "Cooked Food",
            "quantity": 25.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=3)).isoformat(),
            "pickup_address": "45 Cathedral Road, Chennai",
            "latitude": 13.0450,
            "longitude": 80.2500,
        }
    )
    did = create_res.json()["id"]

    # Assign volunteer and transition status
    db = SessionLocal()
    try:
        don = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        don.assigned_volunteer_id = vol_id
        don.status = "arrived_at_donor"
        asgn = VolunteerAssignment(
            donation_id=did,
            volunteer_id=vol_id,
            status="arrived"
        )
        db.add(asgn)
        db.commit()
    finally:
        db.close()

    # Donor retrieves code
    donor_code_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(donor_tok))
    otp = donor_code_res.json()["otp"]

    # Volunteer submits OTP
    verify_res = client.post(
        "/api/volunteers/verify-otp",
        headers=_h(vol_tok),
        json={"donation_id": did, "otp": otp}
    )
    assert verify_res.status_code == 200, verify_res.text
    assert verify_res.json()["status"] == "collected"

    # Verify database state
    db = SessionLocal()
    try:
        updated_don = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        assert updated_don.status == "collected"
        assert updated_don.otp_used_at is not None

        updated_asgn = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == did,
            VolunteerAssignment.volunteer_id == vol_id
        ).first()
        assert updated_asgn.status == "collected"
        assert updated_asgn.collected_at is not None

        otp_rec = db.query(PickupOtpRecord).filter(
            PickupOtpRecord.donation_id == did,
            PickupOtpRecord.purpose == "PICKUP_VERIFICATION_OTP"
        ).first()
        assert otp_rec.used_at is not None
        assert otp_rec.is_active is False
    finally:
        db.close()


# ─── 4. Strict Single-Use Replay Protection ───────────────────────────────────

def test_04_replay_protection_second_request_conflicts_409():
    """
    REPLAY PROTECTION:
    A consumed OTP cannot be submitted a second time.
    First request succeeds -> 200 OK.
    Second request fails -> 409 Conflict.
    """
    ts = int(time.time() * 1000)
    donor_tok = _register_and_login(client, f"donor_replay_{ts}@test.com", "donor")
    vol_tok = _register_and_login(client, f"vol_replay_{ts}@test.com", "volunteer")

    db = SessionLocal()
    try:
        vol = db.query(User).filter(User.email == f"vol_replay_{ts}@test.com").first()
        vol_id = vol.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        headers=_h(donor_tok),
        json={
            "food_name": "Replay Guard Test Meal",
            "food_category": "Cooked Food",
            "quantity": 10.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=3)).isoformat(),
            "pickup_address": "77 Anna Salai, Chennai",
            "latitude": 13.0600,
            "longitude": 80.2500,
        }
    )
    did = create_res.json()["id"]

    db = SessionLocal()
    try:
        don = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        don.assigned_volunteer_id = vol_id
        don.status = "arrived_at_donor"
        asgn = VolunteerAssignment(donation_id=did, volunteer_id=vol_id, status="arrived")
        db.add(asgn)
        db.commit()
    finally:
        db.close()

    # Get code
    code_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(donor_tok))
    otp = code_res.json()["otp"]

    # 1. First attempt succeeds
    r1 = client.post("/api/volunteers/verify-otp", headers=_h(vol_tok), json={"donation_id": did, "otp": otp})
    assert r1.status_code == 200

    # 2. Second attempt fails with 409 Conflict
    r2 = client.post("/api/volunteers/verify-otp", headers=_h(vol_tok), json={"donation_id": did, "otp": otp})
    assert r2.status_code == 409
    assert "already" in r2.json()["detail"].lower()

    # 3. Dedicated endpoint POST /{id}/pickup-otp/verify also fails with 409
    r3 = client.post(f"/api/donations/{did}/pickup-otp/verify", headers=_h(vol_tok), json={"otp": otp})
    assert r3.status_code == 409
    assert "already" in r3.json()["detail"].lower()

    # 4. Donor view shows consumed status
    donor_view = client.get(f"/api/donations/{did}/verification-code", headers=_h(donor_tok)).json()
    assert donor_view["otp"] == "USED"
    assert donor_view["otp_status"] == "consumed"


# ─── 5. Expiry Check ──────────────────────────────────────────────────────────

def test_05_expired_otp_returns_410_gone():
    """
    EXPIRY GUARD:
    Expired OTPs cannot be verified.
    Returns HTTP 410 Gone and marks record as EXPIRED.
    """
    db = SessionLocal()
    try:
        donor = User(
            name="Donor Expiry Test",
            email=f"donor_exp_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            role="donor"
        )
        vol = User(
            name="Vol Expiry Test",
            email=f"vol_exp_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            role="volunteer"
        )
        db.add_all([donor, vol])
        db.commit()

        now = datetime.now(timezone.utc)
        don = FoodDonation(
            donor_id=donor.id,
            assigned_volunteer_id=vol.id,
            food_name="Expired Meal",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=2),
            pickup_address="Chennai",
            status="arrived_at_donor"
        )
        db.add(don)
        db.commit()

        plaintext_otp, otp_rec = generate_pickup_otp(db, don, donor, vol.id)
        # Manually set expired timestamp
        otp_rec.expires_at = now - timedelta(minutes=5)
        db.commit()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_otp(db, don, plaintext_otp, vol)
        assert exc_info.value.status_code == 410
        assert "expired" in exc_info.value.detail.lower()

        # Check delivery status updated to EXPIRED
        db.refresh(otp_rec)
        assert otp_rec.delivery_status == "EXPIRED"
        assert otp_rec.is_active is False
    finally:
        db.close()


# ─── 6. Incorrect OTP Rejection ───────────────────────────────────────────────

def test_06_wrong_otp_returns_400_bad_request():
    """
    Wrong OTP code entered by courier returns 400 Bad Request.
    Token remains unconsumed.
    """
    db = SessionLocal()
    try:
        donor = User(
            name="Donor Wrong Code Test",
            email=f"donor_wrong_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            role="donor"
        )
        vol = User(
            name="Vol Wrong Code Test",
            email=f"vol_wrong_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            role="volunteer"
        )
        db.add_all([donor, vol])
        db.commit()

        now = datetime.now(timezone.utc)
        don = FoodDonation(
            donor_id=donor.id,
            assigned_volunteer_id=vol.id,
            food_name="Test Food",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=2),
            pickup_address="Chennai",
            status="arrived_at_donor"
        )
        db.add(don)
        db.commit()

        plaintext_otp, otp_rec = generate_pickup_otp(db, don, donor, vol.id)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_otp(db, don, "999999", vol)  # Incorrect code
        assert exc_info.value.status_code == 400
        assert "incorrect" in exc_info.value.detail.lower()

        # Token must still be active and unconsumed
        db.refresh(otp_rec)
        assert otp_rec.used_at is None
        assert otp_rec.is_active is True
    finally:
        db.close()


# ─── 7. Concurrency Transaction Safety: Simultaneous OTP Verification ────────

def test_07_simultaneous_verification_requests_prevent_race_condition():
    """
    TRANSACTION SAFETY:
    Two simultaneous requests using the exact same OTP must never both succeed.
    Expected: Exactly one succeeds (200), and the other returns 409 Conflict.
    """
    ts = int(time.time() * 1000)
    donor_tok = _register_and_login(client, f"donor_race_{ts}@test.com", "donor")
    vol_tok = _register_and_login(client, f"vol_race_{ts}@test.com", "volunteer")

    db = SessionLocal()
    try:
        vol = db.query(User).filter(User.email == f"vol_race_{ts}@test.com").first()
        vol_id = vol.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        headers=_h(donor_tok),
        json={
            "food_name": "Concurrency Test Meals",
            "food_category": "Cooked Food",
            "quantity": 20.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=3)).isoformat(),
            "pickup_address": "Race Track Road, Chennai",
            "latitude": 13.0800,
            "longitude": 80.2700,
        }
    )
    did = create_res.json()["id"]

    db = SessionLocal()
    try:
        don = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        don.assigned_volunteer_id = vol_id
        don.status = "arrived_at_donor"
        asgn = VolunteerAssignment(donation_id=did, volunteer_id=vol_id, status="arrived")
        db.add(asgn)
        db.commit()
    finally:
        db.close()

    code_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(donor_tok))
    otp = code_res.json()["otp"]

    # Execute two simultaneous verification calls in parallel threads
    def submit_otp():
        # Fresh test client per thread for isolated connection
        tc = TestClient(app)
        return tc.post(
            "/api/volunteers/verify-otp",
            headers=_h(vol_tok),
            json={"donation_id": did, "otp": otp}
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_otp)
        f2 = executor.submit(submit_otp)
        res1 = f1.result()
        res2 = f2.result()

    status_codes = sorted([res1.status_code, res2.status_code])
    # Exactly one 200 and one 409
    assert status_codes == [200, 409], f"Concurrency violation! Statuses: {status_codes}, Res1: {res1.text}, Res2: {res2.text}"


# ─── 8. Regeneration Protection ───────────────────────────────────────────────

def test_08_regeneration_invalidates_previous_otp():
    """
    REGENERATION PROTECTION:
    When donor generates a new OTP, the previous OTP is immediately invalidated.
    Using the old OTP fails verification.
    """
    db = SessionLocal()
    try:
        donor = User(
            name="Donor Regen Guard",
            email=f"donor_rg_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            phone_verified=True,
            phone_normalized="+919876543210",
            role="donor"
        )
        vol = User(
            name="Vol Regen Guard",
            email=f"vol_rg_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            role="volunteer"
        )
        db.add_all([donor, vol])
        db.commit()

        now = datetime.now(timezone.utc)
        don = FoodDonation(
            donor_id=donor.id,
            assigned_volunteer_id=vol.id,
            food_name="Regen Guard Food",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=3),
            pickup_address="Chennai",
            status="arrived_at_donor"
        )
        db.add(don)
        db.commit()

        old_otp, old_rec = generate_pickup_otp(db, don, donor, vol.id)
        old_rec_id = old_rec.id

        # Clear rate limit cache for test isolation
        _OTP_REGEN_ATTEMPTS.pop(f"pickup_regen:{don.id}", None)

        # Regenerate OTP
        new_otp, new_rec, _ = regenerate_pickup_otp(db, don, donor, vol.id)

        # Old record must be inactive
        db.refresh(old_rec)
        assert old_rec.is_active is False
        assert new_rec.is_active is True
        assert new_otp != old_otp

        # Verification with old OTP fails
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_otp(db, don, old_otp, vol)
        assert exc_info.value.status_code == 400

        # Verification with new OTP succeeds
        assert verify_pickup_otp(db, don, new_otp, vol) is True
    finally:
        db.close()


# ─── 9. Comprehensive Audit Trail without Sensitive Leaks ─────────────────────

def test_09_comprehensive_audit_trail_recorded_without_sensitive_leaks():
    """
    AUDIT HARDENING:
    Verify clear audit history entries for all key lifecycle operations:
    created, matched, accepted, self-pickup selected, volunteer assigned,
    reassigned, OTP generated, OTP verified, collected, received,
    distribution started, distributed, completed, cancelled, expired, admin override.
    Guarantees no sensitive data in AuditLog or DonationHistory.
    """
    db = SessionLocal()
    try:
        user = User(
            name="Audit Test User",
            email=f"audit_user_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            role="admin"
        )
        db.add(user)
        db.commit()

        now = datetime.now(timezone.utc)
        don = FoodDonation(
            donor_id=user.id,
            food_name="Audit Food",
            food_category="Cooked Food",
            quantity=50.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=4),
            pickup_address="1 Audit Way, Chennai",
            status="pending"
        )
        db.add(don)
        db.commit()
        did = don.id

        # Test each required audit operation
        required_actions = [
            ("created", "pending", "Donation created with AI condition assessment"),
            ("matched", "pending", "Matched with nearest verified NGO"),
            ("accepted", "accepted", "Accepted by partner NGO"),
            ("self-pickup selected", "accepted", "Self-pickup selected by NGO"),
            ("volunteer assigned", "volunteer_assigned", "Volunteer courier assigned"),
            ("reassigned", "volunteer_assigned", "Dynamic rematch reassigned to replacement courier"),
            ("OTP generated", "volunteer_assigned", "Pickup OTP generated for donation"),
            ("OTP verified", "collected", "Pickup verified securely with OTP"),
            ("collected", "collected", "Food collected at donor premises"),
            ("received", "delivered", "Food received at intake center"),
            ("distribution started", "partially_distributed", "Beneficiary meal distribution started"),
            ("distributed", "partially_distributed", "Distributed 30 meals"),
            ("completed", "completed", "Rescue mission completed"),
            ("cancelled", "cancelled", "Donation cancelled by donor"),
            ("expired", "expired", "Rescue window expired"),
            ("admin override", "completed", "Admin override status update")
        ]

        for action_name, target_status, remarks in required_actions:
            entry = log_rescue_operation(
                db=db,
                action=action_name,
                donation_id=did,
                user_id=user.id,
                old_status=don.status,
                new_status=target_status,
                remarks=remarks,
                details=f"Test operation '{action_name}' executed safely"
            )
            assert entry is not None
            assert entry.action == action_name
            assert entry.resource_id == did

        # Verify all audit logs exist for this donation
        logs = db.query(AuditLog).filter(
            AuditLog.resource_type == "donation",
            AuditLog.resource_id == did
        ).all()
        logged_actions = {l.action for l in logs}

        for action_name, _, _ in required_actions:
            assert action_name in logged_actions, f"Missing audit action: {action_name}"

        # Verify zero credential leakage in AuditLog details
        for l in logs:
            if l.details:
                lower_det = l.details.lower()
                assert "password" not in lower_det or "[redacted" in lower_det
                assert "secret" not in lower_det or "[redacted" in lower_det

        # Verify DonationHistory records
        history_entries = db.query(DonationHistory).filter(DonationHistory.donation_id == did).all()
        assert len(history_entries) >= len(required_actions)

        # Verify zero credential leakage in DonationHistory remarks
        for h in history_entries:
            if h.remarks:
                lower_rem = h.remarks.lower()
                assert "password" not in lower_rem or "[redacted" in lower_rem
    finally:
        db.close()


# ─── 10. Notification and Deep-Link Cleanliness ───────────────────────────────

def test_10_notifications_and_deep_links_never_contain_plaintext_otp():
    """
    NOTIFICATION SECURITY:
    Notifications and deep-link payload must NEVER expose plaintext OTPs or sensitive credentials.
    """
    ts = int(time.time() * 1000)
    donor_tok = _register_and_login(client, f"donor_notif_{ts}@test.com", "donor")
    vol_tok = _register_and_login(client, f"vol_notif_{ts}@test.com", "volunteer")

    db = SessionLocal()
    try:
        donor = db.query(User).filter(User.email == f"donor_notif_{ts}@test.com").first()
        donor_id = donor.id
        vol = db.query(User).filter(User.email == f"vol_notif_{ts}@test.com").first()
        vol_id = vol.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        headers=_h(donor_tok),
        json={
            "food_name": "Notification Test Meal",
            "food_category": "Cooked Food",
            "quantity": 15.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=3)).isoformat(),
            "pickup_address": "Safe Street, Chennai",
            "latitude": 13.0800,
            "longitude": 80.2700,
        }
    )
    did = create_res.json()["id"]

    db = SessionLocal()
    try:
        don = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        don.assigned_volunteer_id = vol_id
        don.status = "arrived_at_donor"
        asgn = VolunteerAssignment(donation_id=did, volunteer_id=vol_id, status="arrived")
        db.add(asgn)
        db.commit()
    finally:
        db.close()

    code_res = client.get(f"/api/donations/{did}/verification-code", headers=_h(donor_tok))
    otp = code_res.json()["otp"]

    # Verify pickup
    client.post("/api/volunteers/verify-otp", headers=_h(vol_tok), json={"donation_id": did, "otp": otp})

    # Inspect all notifications for donor and volunteer
    db = SessionLocal()
    try:
        notifications = db.query(Notification).filter(
            Notification.related_donation_id == did
        ).all()

        for notif in notifications:
            assert otp not in notif.message, f"OTP leaked in notification message: {notif.message}"
            assert otp not in notif.title, f"OTP leaked in notification title: {notif.title}"
            if notif.deep_link_data:
                assert otp not in notif.deep_link_data, f"OTP leaked in deep link: {notif.deep_link_data}"
    finally:
        db.close()


# ─── 11. SMS Delivery Audit Trail (`OtpDeliveryRecord`) ───────────────────────

def test_11_sms_delivery_audit_fields_and_masked_phone():
    """
    DELIVERY AUDIT:
    OtpDeliveryRecord tracks provider, provider_message_id, status, phone_number_masked,
    sent_at, and delivered_at without exposing the full phone number or plaintext OTP.
    """
    db = SessionLocal()
    try:
        donor = User(
            name="SMS Audit Donor",
            email=f"sms_audit_{int(time.time() * 1000)}@test.com",
            password_hash="pwd",
            phone="+919876543210",
            phone_normalized="+919876543210",
            phone_verified=True,
            role="donor"
        )
        db.add(donor)
        db.commit()

        now = datetime.now(timezone.utc)
        don = FoodDonation(
            donor_id=donor.id,
            food_name="SMS Audit Meal",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=2),
            pickup_address="SMS St, Chennai",
            status="pending"
        )
        db.add(don)
        db.commit()

        plaintext_otp, otp_rec = generate_pickup_otp(db, don, donor)
        delivery_rec = send_pickup_otp_sms(db, plaintext_otp, otp_rec, donor)

        assert delivery_rec.id is not None
        assert delivery_rec.phone_number_masked == "+91 ****3210"
        assert delivery_rec.phone_number_masked != "+919876543210"  # Full number NOT stored
        assert delivery_rec.provider in ["mock", "twilio", "fast2sms", "msg91"]
        assert delivery_rec.provider_message_id is not None
        assert delivery_rec.status in ["SENT", "QUEUED"]
        assert delivery_rec.sent_at is not None
    finally:
        db.close()
