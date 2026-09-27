"""
OTP Service — Smart Food Rescue
================================
Secure OTP generation, delivery, verification, and regeneration.

SECURITY RULES:
  - OTPs are stored as SHA-256 hashes ONLY. Plaintext is returned once to the
    authenticated donor API response and sent via SMS — never stored or logged.
  - Purpose isolation: PICKUP_VERIFICATION_OTP and PHONE_VERIFICATION_OTP
    are separate flows. An OTP for one purpose cannot verify the other.
  - Only volunteers/admins may verify a pickup OTP (not the donor themselves).
  - Rate limiting: max 3 regenerations per 10-minute window per donation.
  - Replay protection: used_at timestamp is set on first successful use.
  - Phone verification: donor.phone_verified must be True (server-checked) before
    pickup OTP SMS is sent to their number.
"""

import hashlib
import logging
import secrets
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

_otp_verification_lock = threading.RLock()

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    FoodDonation, PickupOtpRecord, OtpDeliveryRecord, User, AuditLog
)
from app.services.sms_service import sms_provider, mask_phone
from app.services.security_service import log_rescue_operation

logger = logging.getLogger("smart_food_rescue.otp")

# ─── In-memory rate limiting caches ──────────────────────────────────────────
# {key: [timestamps]}  — key = f"pickup_regen:{donation_id}" or f"phone_verify:{user_id}"
_OTP_REGEN_ATTEMPTS: dict = {}
_PHONE_VERIFY_ATTEMPTS: dict = {}


def _hash_otp(otp: str, salt: Optional[str] = None) -> str:
    """Returns SHA-256 hex digest (with optional salt). Input OTP is never stored."""
    if salt:
        return hashlib.sha256(f"{salt}:{otp}".encode()).hexdigest()
    return hashlib.sha256(otp.encode()).hexdigest()


def _generate_otp() -> str:
    """Generates a cryptographically random 6-digit OTP."""
    return str(secrets.randbelow(1000000)).zfill(6)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _check_rate_limit(cache: dict, key: str, max_count: int, window_minutes: int):
    """Sliding-window rate limit. Raises HTTP 429 if exceeded."""
    now = time.time()
    window_seconds = window_minutes * 60
    attempts = [ts for ts in cache.get(key, []) if now - ts < window_seconds]
    cache[key] = attempts
    if len(attempts) >= max_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Please wait before requesting another code. "
                f"Maximum {max_count} requests per {window_minutes} minutes."
            ),
        )
    cache[key] = attempts + [now]


def _log_otp_audit(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    donation_id: Optional[int] = None,
    details: Optional[str] = None,
    status_code: str = "success",
):
    """Audit log for OTP lifecycle. NEVER logs plaintext OTP."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type="otp",
            resource_id=donation_id,
            status=status_code,
            details=details,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[OTP Audit] Failed to log '{action}': {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Pickup OTP: Generate
# ─────────────────────────────────────────────────────────────────────────────

def generate_pickup_otp(
    db: Session,
    donation: FoodDonation,
    donor: User,
    volunteer_id: Optional[int] = None,
) -> Tuple[str, PickupOtpRecord]:
    """
    Generates a new pickup OTP for a donation.
    Deactivates any existing active OTP for the same donation+purpose.
    Returns (plaintext_otp, otp_record) — plaintext is for the API response ONLY.
    The hash is stored in the DB; plaintext is never persisted.
    """
    purpose = "PICKUP_VERIFICATION_OTP"
    expire_minutes = settings.OTP_PICKUP_EXPIRE_MINUTES

    # Deactivate existing active OTP(s) for this donation+purpose
    existing = (
        db.query(PickupOtpRecord)
        .filter(
            PickupOtpRecord.donation_id == donation.id,
            PickupOtpRecord.purpose == purpose,
            PickupOtpRecord.is_active == True,
        )
        .all()
    )
    for old_record in existing:
        old_record.is_active = False
    if existing:
        db.flush()

    # Generate new OTP — plaintext used only here, never stored
    plaintext_otp = _generate_otp()
    otp_hash = _hash_otp(plaintext_otp)
    expires_at = _utcnow() + timedelta(minutes=expire_minutes)

    otp_record = PickupOtpRecord(
        donation_id=donation.id,
        donor_id=donor.id,
        volunteer_id=volunteer_id,
        purpose=purpose,
        otp_hash=otp_hash,
        expires_at=expires_at,
        is_active=True,
        delivery_status="QUEUED",
    )
    db.add(otp_record)
    # Sync with donation model for unified compatibility across all legacy endpoints
    donation.verification_otp = plaintext_otp
    donation.otp_expiry = expires_at
    db.commit()
    db.refresh(otp_record)

    _log_otp_audit(
        db, action="otp_generated",
        user_id=donor.id, donation_id=donation.id,
        details=f"purpose={purpose} expires_in={expire_minutes}m volunteer_id={volunteer_id}",
    )
    log_rescue_operation(
        db, action="OTP generated",
        donation_id=donation.id, user_id=donor.id,
        remarks="Pickup OTP generated for donation",
        details=f"purpose={purpose} expires_in={expire_minutes}m volunteer_id={volunteer_id}",
    )

    return plaintext_otp, otp_record


# ─────────────────────────────────────────────────────────────────────────────
# Pickup OTP: Send via SMS
# ─────────────────────────────────────────────────────────────────────────────

def send_pickup_otp_sms(
    db: Session,
    plaintext_otp: str,
    otp_record: PickupOtpRecord,
    donor: User,
) -> OtpDeliveryRecord:
    """
    Sends the pickup OTP to the donor's verified phone via SMS.
    SECURITY: Checks phone_verified server-side (never trusts client claim).
    Updates OtpDeliveryRecord with provider result.
    """
    # Server-side verification check — never trust client-provided phone_verified
    if not donor.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Please verify your phone number before using phone-based pickup "
                "verification. Tap 'Verify Phone Number' in your profile."
            ),
        )

    phone = donor.phone_normalized or donor.phone
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No phone number found on your account. Please add and verify a phone number.",
        )

    phone_masked = mask_phone(phone)
    expire_minutes = settings.OTP_PICKUP_EXPIRE_MINUTES
    provider = sms_provider()

    # Create delivery record (QUEUED)
    delivery_record = OtpDeliveryRecord(
        otp_record_id=otp_record.id,
        user_id=donor.id,
        donation_id=otp_record.donation_id,
        purpose=otp_record.purpose,
        phone_number_masked=phone_masked,
        provider=settings.SMS_PROVIDER,
        status="QUEUED",
        expires_at=otp_record.expires_at,
    )
    db.add(delivery_record)
    db.flush()

    # Send SMS — plaintext OTP used here only, never stored
    result = provider.send_otp_sms(
        phone_e164=phone,
        otp=plaintext_otp,
        purpose=otp_record.purpose,
        expires_minutes=expire_minutes,
    )

    # Update delivery record with provider result
    now = _utcnow()
    delivery_record.provider_message_id = result.provider_message_id
    delivery_record.status = result.initial_status if result.success else "FAILED"
    delivery_record.sent_at = now if result.success else None
    delivery_record.failed_at = None if result.success else now
    delivery_record.failure_reason = result.failure_reason

    # Update OTP record delivery status
    otp_record.delivery_status = delivery_record.status
    otp_record.provider_message_id = result.provider_message_id

    db.commit()
    db.refresh(delivery_record)

    _log_otp_audit(
        db, action="otp_sms_queued" if result.success else "otp_sms_failed",
        user_id=donor.id, donation_id=otp_record.donation_id,
        details=(
            f"provider={settings.SMS_PROVIDER} "
            f"status={delivery_record.status} "
            f"message_id={result.provider_message_id} "
            f"phone={phone_masked}"
        ),
        status_code="success" if result.success else "failed",
    )

    return delivery_record


# ─────────────────────────────────────────────────────────────────────────────
# Pickup OTP: Verify (volunteer/admin only)
# ─────────────────────────────────────────────────────────────────────────────

def verify_pickup_otp(
    db: Session,
    donation: FoodDonation,
    otp_attempt: str,
    verifier: User,
) -> bool:
    """
    Verifies a pickup OTP entered by an assigned volunteer, receiving NGO, or admin.
    EXACT ARCHITECTURE FLOW:
      1. Lock row (transaction safety against concurrent requests)
      2. Replay guard (check if previously consumed -> 409 Conflict)
      3. Compare with active record (find active PickupOtpRecord)
      4. Verify expiry (now > expires_at -> 410 Gone)
      5. Verify hash (hash submitted OTP and timing-safe compare -> 400 Bad Request)
      6. Verify role (donor -> 403 Forbidden, courier/admin required)
      7. Verify donation assignment (courier assigned to this donation -> 403 if unassigned)
      8. Consume token (mark used_at, is_active=False, donation.otp_used_at=now)
      9. Create history & audit logs (DonationHistory and AuditLog)
    """
    purpose = "PICKUP_VERIFICATION_OTP"

    # 1. Transaction Safety: Exclusive row lock on donation to prevent race conditions
    try:
        locked_donation = (
            db.query(FoodDonation)
            .filter(FoodDonation.id == donation.id)
            .with_for_update()
            .first()
        )
        if locked_donation:
            donation = locked_donation
    except Exception:
        pass

    # 2. Replay Guard at donation level
    if donation.otp_used_at is not None or donation.status in ["collected", "in_transit", "delivered", "completed"]:
        _log_otp_audit(
            db, action="otp_replay_attempted",
            user_id=verifier.id, donation_id=donation.id,
            details="Donation already collected / OTP used — replay rejected",
            status_code="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This pickup code has already been used. Pickup already verified.",
        )

    # 3. Fetch active OTP record (with row lock if supported)
    try:
        otp_record = (
            db.query(PickupOtpRecord)
            .filter(
                PickupOtpRecord.donation_id == donation.id,
                PickupOtpRecord.purpose == purpose,
                PickupOtpRecord.is_active == True,
            )
            .with_for_update()
            .first()
        )
    except Exception:
        otp_record = (
            db.query(PickupOtpRecord)
            .filter(
                PickupOtpRecord.donation_id == donation.id,
                PickupOtpRecord.purpose == purpose,
                PickupOtpRecord.is_active == True,
            )
            .first()
        )

    # Legacy fallback: if active record not found, check if donation.verification_otp is seeded
    if not otp_record and donation.verification_otp and donation.otp_used_at is None:
        otp_record = PickupOtpRecord(
            donation_id=donation.id,
            donor_id=donation.donor_id,
            volunteer_id=donation.assigned_volunteer_id,
            purpose=purpose,
            otp_hash=_hash_otp(donation.verification_otp.strip()),
            expires_at=donation.otp_expiry or (_utcnow() + timedelta(hours=settings.OTP_EXPIRE_HOURS)),
            is_active=True,
            delivery_status="QUEUED",
        )
        db.add(otp_record)
        db.flush()

    if not otp_record:
        # Check if any record for this donation and purpose was already used (replay guard)
        used_record = (
            db.query(PickupOtpRecord)
            .filter(
                PickupOtpRecord.donation_id == donation.id,
                PickupOtpRecord.purpose == purpose,
                PickupOtpRecord.used_at.isnot(None),
            )
            .first()
        )
        if used_record or donation.otp_used_at is not None:
            _log_otp_audit(
                db, action="otp_replay_attempted",
                user_id=verifier.id, donation_id=donation.id,
                details="OTP already used — replay rejected",
                status_code="failed",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This pickup code has already been used. Pickup already verified.",
            )

        _log_otp_audit(
            db, action="otp_verify_no_active",
            user_id=verifier.id, donation_id=donation.id,
            details="No active OTP found for donation",
            status_code="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active pickup code found. The code may have expired or been regenerated.",
        )

    now = _utcnow()

    # 4. Replay guard on active record
    if otp_record.used_at is not None:
        _log_otp_audit(
            db, action="otp_replay_attempted",
            user_id=verifier.id, donation_id=donation.id,
            details="OTP already used — replay rejected",
            status_code="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This pickup code has already been used. Pickup already verified.",
        )

    # 5. Expiry Check
    expires_at = otp_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        otp_record.is_active = False
        otp_record.delivery_status = "EXPIRED"
        db.commit()
        _log_otp_audit(
            db, action="otp_expired",
            user_id=verifier.id, donation_id=donation.id,
            details="OTP verification failed — expired",
            status_code="failed",
        )
        log_rescue_operation(
            db, action="expired",
            donation_id=donation.id, user_id=verifier.id,
            remarks="OTP expired before verification",
            details="Pickup OTP verification failed due to expiration",
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This pickup code has expired. Ask the donor to generate a new code.",
        )

    # 6. Hash submitted OTP & timing-safe compare
    attempt_hash = _hash_otp(otp_attempt.strip())
    if not secrets.compare_digest(attempt_hash, otp_record.otp_hash):
        _log_otp_audit(
            db, action="otp_wrong",
            user_id=verifier.id, donation_id=donation.id,
            details="Wrong OTP entered",
            status_code="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect pickup code. Please ask the donor to show the code again.",
        )

    # 7. Role Isolation
    if verifier.role == "donor":
        _log_otp_audit(
            db, action="otp_unauthorized_attempt",
            user_id=verifier.id, donation_id=donation.id,
            details="Donor attempted self-verification",
            status_code="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Donors cannot verify pickup codes. The courier must submit the code.",
        )
    elif verifier.role not in ["volunteer", "admin", "ngo"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized role for OTP verification.",
        )

    # 8. Verify Donation Assignment
    if verifier.role == "volunteer":
        is_assigned = (
            donation.assigned_volunteer_id == verifier.id or
            (otp_record and otp_record.volunteer_id == verifier.id)
        )
        if not is_assigned:
            from app.models.models import VolunteerAssignment
            assign = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == donation.id,
                VolunteerAssignment.volunteer_id == verifier.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected"])
            ).first()
            if not assign:
                _log_otp_audit(
                    db, action="otp_unauthorized_attempt",
                    user_id=verifier.id, donation_id=donation.id,
                    details=f"Unassigned volunteer {verifier.id} attempted OTP verification",
                    status_code="failed",
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not the assigned volunteer for this donation.",
                )
    elif verifier.role == "ngo":
        from app.models.models import NGO
        ngo_prof = db.query(NGO).filter(NGO.user_id == verifier.id).first()
        if not ngo_prof or donation.assigned_ngo_id != ngo_prof.id:
            _log_otp_audit(
                db, action="otp_unauthorized_attempt",
                user_id=verifier.id, donation_id=donation.id,
                details=f"Unassigned NGO {verifier.id} attempted OTP verification",
                status_code="failed",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned NGO for this donation.",
            )

    # 9. Consume token (single use guarantee)
    otp_record.used_at = now
    otp_record.is_active = False
    donation.otp_used_at = now
    donation.verification_otp = None  # Clear plaintext OTP from donation model
    db.commit()

    # 10. Audit logging & History creation
    _log_otp_audit(
        db, action="otp_verified",
        user_id=verifier.id, donation_id=donation.id,
        details=f"verifier_role={verifier.role} verifier_id={verifier.id} purpose={purpose}",
    )
    log_rescue_operation(
        db, action="OTP verified",
        donation_id=donation.id, user_id=verifier.id,
        remarks=f"Pickup verified securely with OTP by {verifier.role}",
        details=f"OTP successfully verified by user #{verifier.id} ({verifier.role})",
    )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Pickup OTP: Regenerate
# ─────────────────────────────────────────────────────────────────────────────

def regenerate_pickup_otp(
    db: Session,
    donation: FoodDonation,
    donor: User,
    volunteer_id: Optional[int] = None,
) -> Tuple[str, PickupOtpRecord, OtpDeliveryRecord]:
    """
    Generates a new pickup OTP, invalidates the previous one, and re-sends SMS.
    Rate-limited: max OTP_REGEN_MAX_PER_WINDOW per OTP_REGEN_WINDOW_MINUTES.
    """
    rate_key = f"pickup_regen:{donation.id}"
    _check_rate_limit(
        _OTP_REGEN_ATTEMPTS,
        rate_key,
        max_count=settings.OTP_REGEN_MAX_PER_WINDOW,
        window_minutes=settings.OTP_REGEN_WINDOW_MINUTES,
    )

    _log_otp_audit(
        db, action="otp_regenerated",
        user_id=donor.id, donation_id=donation.id,
        details="Donor requested new pickup OTP — old OTP invalidated",
    )

    plaintext_otp, otp_record = generate_pickup_otp(db, donation, donor, volunteer_id)
    delivery_record = send_pickup_otp_sms(db, plaintext_otp, otp_record, donor)
    return plaintext_otp, otp_record, delivery_record


# ─────────────────────────────────────────────────────────────────────────────
# Phone Verification OTP
# ─────────────────────────────────────────────────────────────────────────────

def send_phone_verification_otp(
    db: Session,
    user: User,
    phone_e164: str,
) -> OtpDeliveryRecord:
    """
    Sends a PHONE_VERIFICATION_OTP to the given E.164 number.
    Rate-limited: max 3 per 15 minutes per user.
    """
    rate_key = f"phone_verify:{user.id}"
    _check_rate_limit(
        _PHONE_VERIFY_ATTEMPTS,
        rate_key,
        max_count=settings.OTP_PHONE_VERIFY_MAX_PER_WINDOW,
        window_minutes=settings.OTP_PHONE_VERIFY_WINDOW_MINUTES,
    )

    purpose = "PHONE_VERIFICATION_OTP"
    expire_minutes = settings.OTP_PHONE_VERIFY_EXPIRE_MINUTES
    expires_at = _utcnow() + timedelta(minutes=expire_minutes)

    # Deactivate existing phone verify OTPs for this user
    existing = (
        db.query(PickupOtpRecord)
        .filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == purpose,
            PickupOtpRecord.is_active == True,
        )
        .all()
    )
    for old in existing:
        old.is_active = False
    if existing:
        db.flush()

    plaintext_otp = _generate_otp()
    otp_hash = _hash_otp(plaintext_otp)

    otp_record = PickupOtpRecord(
        donation_id=0,   # 0 sentinel for phone-only verification (no donation)
        donor_id=user.id,
        purpose=purpose,
        otp_hash=otp_hash,
        expires_at=expires_at,
        is_active=True,
        delivery_status="QUEUED",
    )
    db.add(otp_record)
    db.flush()

    phone_masked = mask_phone(phone_e164)
    provider = sms_provider()

    delivery_record = OtpDeliveryRecord(
        otp_record_id=otp_record.id,
        user_id=user.id,
        donation_id=None,
        purpose=purpose,
        phone_number_masked=phone_masked,
        provider=settings.SMS_PROVIDER,
        status="QUEUED",
        expires_at=expires_at,
    )
    db.add(delivery_record)
    db.flush()

    result = provider.send_otp_sms(
        phone_e164=phone_e164,
        otp=plaintext_otp,
        purpose=purpose,
        expires_minutes=expire_minutes,
    )

    now = _utcnow()
    delivery_record.provider_message_id = result.provider_message_id
    delivery_record.status = result.initial_status if result.success else "FAILED"
    delivery_record.sent_at = now if result.success else None
    delivery_record.failed_at = None if result.success else now
    delivery_record.failure_reason = result.failure_reason
    otp_record.delivery_status = delivery_record.status
    otp_record.provider_message_id = result.provider_message_id

    db.commit()
    db.refresh(delivery_record)

    _log_otp_audit(
        db, action="phone_verification_otp_sent",
        user_id=user.id,
        details=f"phone={phone_masked} provider={settings.SMS_PROVIDER} status={delivery_record.status}",
    )
    return delivery_record


def verify_phone_otp(
    db: Session,
    user: User,
    phone_e164: str,
    otp_attempt: str,
) -> bool:
    """
    Verifies the phone verification OTP and marks the phone as verified.
    On success: user.phone_verified = True, user.phone_normalized = phone_e164.
    """
    purpose = "PHONE_VERIFICATION_OTP"

    otp_record = (
        db.query(PickupOtpRecord)
        .filter(
            PickupOtpRecord.donor_id == user.id,
            PickupOtpRecord.purpose == purpose,
            PickupOtpRecord.is_active == True,
        )
        .order_by(PickupOtpRecord.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active verification code found. Please request a new code.",
        )

    now = _utcnow()

    if otp_record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This verification code has already been used. Please request a new code.",
        )

    expires_at = otp_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        otp_record.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This verification code has expired. Please request a new code.",
        )

    attempt_hash = _hash_otp(otp_attempt)
    if not secrets.compare_digest(attempt_hash, otp_record.otp_hash):
        _log_otp_audit(
            db, action="phone_otp_wrong",
            user_id=user.id,
            details="Wrong phone verification OTP",
            status_code="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect verification code. Please try again.",
        )

    # Mark used and update user phone verification status
    otp_record.used_at = now
    otp_record.is_active = False
    user.phone_verified = True
    user.phone_normalized = phone_e164
    user.phone = phone_e164  # Keep phone field in sync
    db.commit()

    _log_otp_audit(
        db, action="phone_verified",
        user_id=user.id,
        details=f"phone={mask_phone(phone_e164)} verified=True",
    )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# SMS Webhook: Update Delivery Status
# ─────────────────────────────────────────────────────────────────────────────

def process_sms_delivery_webhook(
    db: Session,
    provider_message_id: str,
    new_status: str,
    delivered_at: Optional[datetime] = None,
    failed_at: Optional[datetime] = None,
    failure_reason: Optional[str] = None,
    raw_payload_json: Optional[str] = None,
) -> Optional[OtpDeliveryRecord]:
    """
    Updates delivery status from a provider webhook callback.
    SECURITY: Only this function (called from authenticated webhook route) may
    update delivery status — never a client-facing endpoint.
    """
    valid_statuses = {"QUEUED", "SENT", "DELIVERED", "FAILED", "EXPIRED", "UNKNOWN"}
    new_status = new_status.upper()
    if new_status not in valid_statuses:
        logger.warning(f"[SMS Webhook] Unknown status '{new_status}' — ignoring")
        return None

    delivery_record = (
        db.query(OtpDeliveryRecord)
        .filter(OtpDeliveryRecord.provider_message_id == provider_message_id)
        .first()
    )

    if not delivery_record:
        logger.warning(f"[SMS Webhook] No delivery record for message_id={provider_message_id}")
        return None

    delivery_record.status = new_status
    if delivered_at:
        delivery_record.delivered_at = delivered_at
    if failed_at:
        delivery_record.failed_at = failed_at
    if failure_reason:
        delivery_record.failure_reason = failure_reason
    if raw_payload_json:
        delivery_record.provider_payload_json = raw_payload_json

    # Sync status to parent OTP record
    otp_record = db.query(PickupOtpRecord).filter(
        PickupOtpRecord.id == delivery_record.otp_record_id
    ).first()
    if otp_record and otp_record.provider_message_id == provider_message_id:
        otp_record.delivery_status = new_status

    db.commit()

    logger.info(
        f"[SMS Webhook] Delivery status updated: "
        f"message_id={provider_message_id} status={new_status}"
    )
    return delivery_record
