from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token, RefreshRequest
from app.models.models import User, NGO, Reward
from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_refresh_token, hash_token_for_storage
)
from app.core.dependencies import get_current_user
from app.services.security_service import (
    check_login_rate_limit, record_login_failure, reset_login_failures, log_audit_event
)
from app.services.otp_service import send_phone_verification_otp, verify_phone_otp
from app.services.sms_service import mask_phone

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    role_norm = user_in.role.lower().strip()
    allowed_roles = ["donor", "ngo", "volunteer", "admin"]
    if role_norm not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{user_in.role}'. Allowed roles: {', '.join(allowed_roles)}."
        )

    # 1. Controlled Admin Creation check
    if role_norm == "admin":
        if not user_in.admin_secret or user_in.admin_secret != settings.ADMIN_PROVISIONING_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public admin registration is not permitted. Admin accounts require authorized setup credentials."
            )

    # 2. Validation checks
    if len(user_in.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered."
        )

    if user_in.phone:
        existing_phone = db.query(User).filter(User.phone == user_in.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already registered."
            )

    if role_norm == "volunteer":
        allowed_vehicles = ["walking", "bike", "car", "van"]
        if user_in.vehicle_type and user_in.vehicle_type.lower() not in allowed_vehicles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid vehicle type '{user_in.vehicle_type}'. Allowed: {', '.join(allowed_vehicles)}."
            )

    if role_norm == "ngo":
        org_name = user_in.organization_name or user_in.name
        if not org_name or not org_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name is required for NGO registration."
            )

    hashed_pwd = hash_password(user_in.password)

    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_pwd,
        phone=user_in.phone,
        role=role_norm,
        address=user_in.address,
        latitude=user_in.latitude,
        longitude=user_in.longitude,
        vehicle_type=user_in.vehicle_type if role_norm == "volunteer" else "bike",
        carrying_capacity=user_in.carrying_capacity if role_norm == "volunteer" else 50,
        is_active=False if role_norm == "volunteer" else True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if new_user.role == "ngo":
        ngo_profile = NGO(
            user_id=new_user.id,
            organization_name=user_in.organization_name or user_in.name,
            description=user_in.description or "Community food support organization",
            address=user_in.address,
            latitude=user_in.latitude,
            longitude=user_in.longitude,
            capacity=user_in.capacity or 100,
            current_capacity=user_in.capacity or 100,
            contact_phone=user_in.phone,
            operating_hours=user_in.operating_hours,
            demand_requirements=user_in.demand_requirements,
            is_verified=False
        )
        db.add(ngo_profile)

    if new_user.role == "donor":
        reward = Reward(user_id=new_user.id, points=0, level="Bronze")
        db.add(reward)

    db.commit()
    return new_user

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    # Determine identifier for rate limiting (IP + email/phone)
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{user_in.email.lower()}"

    # Rate limit check — raises HTTP 429 if threshold exceeded
    check_login_rate_limit(rate_limit_key)

    # Authenticate — use generic error to prevent user enumeration
    user = db.query(User).filter(
        (User.email == user_in.email) | (User.phone == user_in.email)
    ).first()

    if not user or not verify_password(user_in.password, user.password_hash):
        record_login_failure(rate_limit_key)
        log_audit_event(
            db, action="login_failed",
            resource_type="user",
            ip_address=client_ip,
            status_code="failed",
            details=f"Failed login attempt for identifier: {user_in.email[:30]}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )

    if not user.is_active and user.role != "volunteer":
        log_audit_event(
            db, action="login_blocked_inactive",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=client_ip,
            status_code="blocked",
            details="Login attempt on deactivated account"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact administrator."
        )

    # Successful login — reset failure counter
    reset_login_failures(rate_limit_key)

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "role": user.role})

    # Store hashed refresh token (never store raw tokens in DB)
    user.refresh_token_hash = hash_token_for_storage(refresh_token)
    db.commit()

    log_audit_event(
        db, action="login_success",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=client_ip,
        status_code="success",
        details=f"Successful login for role={user.role}"
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        name=user.name,
        email=user.email
    )

@router.post("/refresh", response_model=Token)
def refresh_access_token(refresh_req: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchanges a valid refresh token for a new access token + rotated refresh token.
    Verifies the token is not revoked by checking the stored hash.
    """
    payload = decode_refresh_token(refresh_req.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Verify token hasn't been revoked (hash comparison)
    provided_hash = hash_token_for_storage(refresh_req.refresh_token)
    if not user.refresh_token_hash or user.refresh_token_hash != provided_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked. Please log in again."
        )

    if not user.is_active and user.role != "volunteer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact the platform administrator."
        )

    # Rotate: issue new access + refresh tokens
    new_access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id), "role": user.role})
    user.refresh_token_hash = hash_token_for_storage(new_refresh_token)
    db.commit()

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        name=user.name,
        email=user.email
    )

@router.post("/logout")
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Revokes the stored refresh token hash, invalidating the session for refresh."""
    current_user.refresh_token_hash = None
    db.commit()
    log_audit_event(
        db, action="logout",
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        status_code="success",
        details="User logged out — refresh token revoked"
    )
    return {"message": "Logged out successfully."}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# Phone Number Verification
# ─────────────────────────────────────────────────────────────────────────────

class PhoneVerificationRequest(BaseModel):
    phone_number: str     # Raw phone number as entered
    country_code: str = "+91"  # E.g. "+91" for India

class PhoneVerifyOtpRequest(BaseModel):
    phone_number: str
    country_code: str = "+91"
    otp: str


def _normalize_e164(phone: str, country_code: str) -> str:
    """Converts a phone number to E.164 format (e.g. +919876543210)."""
    # Strip all non-digits from phone
    digits = ''.join(c for c in phone if c.isdigit())
    code = country_code.replace('+', '').replace(' ', '')
    # If number already contains country code, don't double-add
    if digits.startswith(code):
        return f"+{digits}"
    return f"+{code}{digits}"


@router.post("/phone/send-verification")
def send_phone_verification(
    payload: PhoneVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sends a PHONE_VERIFICATION_OTP to the provided phone number.
    Rate-limited: max 3 per 15 minutes per user.
    Requires authentication — phone is tied to the logged-in user.

    SECURITY:
    - This flow uses PHONE_VERIFICATION_OTP purpose.
    - It cannot be used to verify a pickup OTP (separate purpose).
    """
    phone_e164 = _normalize_e164(payload.phone_number, payload.country_code)
    delivery_record = send_phone_verification_otp(db, current_user, phone_e164)
    masked = mask_phone(phone_e164)
    return {
        "message": f"Verification code sent to {masked}.",
        "phone_masked": masked,
        "delivery_status": delivery_record.status,
        "expires_in_minutes": 10,
        "note": "Delivery confirmation unavailable with current SMS provider." if delivery_record.status == "SENT" else None,
    }


@router.post("/phone/verify")
def verify_phone_number(
    payload: PhoneVerifyOtpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verifies the phone OTP and marks the user's phone as verified.
    On success: phone_verified=True, phone_normalized=E.164 stored.

    SECURITY:
    - Server checks the hash — never trusts client-provided phone_verified=true.
    - Separate from pickup OTP verification (different purpose).
    """
    phone_e164 = _normalize_e164(payload.phone_number, payload.country_code)
    verify_phone_otp(db, current_user, phone_e164, payload.otp)
    masked = mask_phone(phone_e164)
    return {
        "message": f"Phone number verified successfully.",
        "phone_masked": masked,
        "phone_verified": True,
    }


@router.get("/phone/status")
def get_phone_verification_status(
    current_user: User = Depends(get_current_user),
):
    """Returns the current user's phone verification status."""
    return {
        "phone_verified": current_user.phone_verified,
        "phone_masked": mask_phone(current_user.phone_normalized or current_user.phone or "") if current_user.phone else None,
        "phone_country_code": current_user.phone_country_code,
    }
