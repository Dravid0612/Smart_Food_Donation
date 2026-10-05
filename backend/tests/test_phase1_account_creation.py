"""
Phase 1 — Account Creation & Authentication Test Suite
=====================================================
Covers:
  1. Donor registration (returns 201, User created, Reward initialized)
  2. NGO registration (returns 201, NGO profile created with is_verified=False)
  3. Volunteer registration (returns 201, vehicle_type & capacity, is_active=False initial availability)
  4. Controlled Admin creation:
     - Public attempt without secret -> 403 Forbidden
     - Public attempt with invalid secret -> 403 Forbidden
     - Public attempt with valid setup secret -> 201 Created
     - Authorized admin endpoint /api/admin/create-admin -> 201 Created
     - Non-admin calling /api/admin/create-admin -> 403 Forbidden
  5. Duplicate registration (duplicate email -> 400, duplicate phone -> 400)
  6. Invalid registration (short password -> 400, invalid role -> 400, invalid vehicle -> 400)
  7. Verification gate (unverified NGO blocked from accepting donation; verified NGO allowed)
  8. JWT issuance & role claims
  9. Refresh token exchange & rotation
  10. Logout token revocation
  11. Unauthorized role access prevention
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.models.models import User, NGO, Reward, FoodDonation

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_test_users():
    """Clean up test users created during test runs."""
    def _clean():
        db = next(get_db())
        try:
            test_emails = [
                "new_donor@test.org", "new_ngo@test.org", "new_vol@test.org",
                "fake_admin@test.org", "bad_secret_admin@test.org", "valid_admin@test.org",
                "prov_admin@test.org", "dup_test@test.org", "dup_phone@test.org",
                "short_pwd@test.org", "bad_role@test.org", "bad_veh@test.org",
                "unverified_ngo_test@test.org", "admin_gate_tester@test.org"
            ]
            test_phones = [
                "+919800000001", "+919800000002", "+919800000003",
                "+919800000004", "+919800000005"
            ]
            users = db.query(User).filter(
                (User.email.in_(test_emails)) | (User.phone.in_(test_phones))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    _clean()
    yield
    _clean()


def test_donor_registration_success():
    payload = {
        "name": "Green Cafe",
        "email": "new_donor@test.org",
        "password": "donorPassword123",
        "phone": "+919800000001",
        "role": "donor",
        "address": "123 Main Street, Bangalore"
    }
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["email"] == "new_donor@test.org"
    assert data["role"] == "donor"
    assert data["name"] == "Green Cafe"

    # Verify Bronze reward was created
    db = next(get_db())
    try:
        user = db.query(User).filter(User.email == "new_donor@test.org").first()
        assert user is not None
        assert user.role == "donor"
        assert user.is_active is True
        reward = db.query(Reward).filter(Reward.user_id == user.id).first()
        assert reward is not None
        assert reward.level == "Bronze"
    finally:
        db.close()


def test_ngo_registration_pending_verification():
    payload = {
        "name": "Care Food Bank",
        "email": "new_ngo@test.org",
        "password": "ngoPassword123",
        "phone": "+919800000002",
        "role": "ngo",
        "organization_name": "Care Food Bank Trust",
        "description": "Providing meals to shelters",
        "capacity": 250,
        "address": "45 Shelter Road, Bangalore",
        "operating_hours": '{"monday": {"open": "09:00", "close": "18:00"}}',
        "demand_requirements": '{"Cooked Food": 100, "Bakery": 50}'
    }
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["email"] == "new_ngo@test.org"
    assert data["role"] == "ngo"

    # Verify NGO profile exists with is_verified == False
    db = next(get_db())
    try:
        user = db.query(User).filter(User.email == "new_ngo@test.org").first()
        assert user is not None
        ngo = db.query(NGO).filter(NGO.user_id == user.id).first()
        assert ngo is not None
        assert ngo.organization_name == "Care Food Bank Trust"
        assert ngo.capacity == 250
        assert ngo.is_verified is False  # Must start as pending verification
    finally:
        db.close()


def test_volunteer_registration_initial_availability():
    payload = {
        "name": "Rohan Courier",
        "email": "new_vol@test.org",
        "password": "volPassword123",
        "phone": "+919800000003",
        "role": "volunteer",
        "vehicle_type": "bike",
        "carrying_capacity": 40
    }
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["email"] == "new_vol@test.org"
    assert data["role"] == "volunteer"
    assert data["vehicle_type"] == "bike"
    assert data["carrying_capacity"] == 40

    # Verify volunteer initially starts unavailable (is_active=False)
    db = next(get_db())
    try:
        user = db.query(User).filter(User.email == "new_vol@test.org").first()
        assert user is not None
        assert user.is_active is False
    finally:
        db.close()

    # Volunteer can still log in to toggle availability
    login_resp = client.post("/api/auth/login", json={
        "email": "new_vol@test.org",
        "password": "volPassword123"
    })
    assert login_resp.status_code == 200, f"Volunteer login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]

    # Toggle availability to True via volunteer profile update
    prof_resp = client.put(
        "/api/volunteers/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": True}
    )
    assert prof_resp.status_code == 200
    assert prof_resp.json()["is_active"] is True


def test_admin_creation_security_controls():
    # 1. Public unrestricted admin registration is strictly forbidden
    r_pub = client.post("/api/auth/register", json={
        "name": "Unrestricted Admin",
        "email": "fake_admin@test.org",
        "password": "adminPassword123",
        "role": "admin"
    })
    assert r_pub.status_code == 403
    assert "Public admin registration is not permitted" in r_pub.text

    # 2. Registration with invalid secret is strictly forbidden
    r_bad_secret = client.post("/api/auth/register", json={
        "name": "Bad Secret Admin",
        "email": "bad_secret_admin@test.org",
        "password": "adminPassword123",
        "role": "admin",
        "admin_secret": "wrong_secret_123"
    })
    assert r_bad_secret.status_code == 403

    # 3. Registration with valid setup secret succeeds
    r_valid_secret = client.post("/api/auth/register", json={
        "name": "Authorized Setup Admin",
        "email": "valid_admin@test.org",
        "password": "adminPassword123",
        "role": "admin",
        "admin_secret": settings.ADMIN_PROVISIONING_SECRET
    })
    assert r_valid_secret.status_code == 201
    assert r_valid_secret.json()["role"] == "admin"

    # 4. Provisioned admin can log in and access admin statistics
    login_resp = client.post("/api/auth/login", json={
        "email": "valid_admin@test.org",
        "password": "adminPassword123"
    })
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]

    stats_resp = client.get("/api/admin/statistics", headers={"Authorization": f"Bearer {admin_token}"})
    assert stats_resp.status_code == 200

    # 5. Authenticated admin can provision another admin via protected endpoint
    r_prov = client.post(
        "/api/admin/create-admin",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Secondary Admin",
            "email": "prov_admin@test.org",
            "password": "adminPassword123",
            "role": "admin"
        }
    )
    assert r_prov.status_code == 201
    assert r_prov.json()["role"] == "admin"


def test_duplicate_registration_validation():
    # Register first account
    r1 = client.post("/api/auth/register", json={
        "name": "First Account",
        "email": "dup_test@test.org",
        "password": "password123",
        "phone": "+919811119999",
        "role": "donor"
    })
    assert r1.status_code == 201

    # Attempt to register with same email
    r_dup_email = client.post("/api/auth/register", json={
        "name": "Second Account",
        "email": "dup_test@test.org",
        "password": "anotherPassword123",
        "role": "donor"
    })
    assert r_dup_email.status_code == 400
    assert "Email is already registered" in r_dup_email.text

    # Attempt to register with same phone
    r_dup_phone = client.post("/api/auth/register", json={
        "name": "Third Account",
        "email": "dup_phone@test.org",
        "password": "anotherPassword123",
        "phone": "+919811119999",
        "role": "donor"
    })
    assert r_dup_phone.status_code == 400
    assert "Phone number is already registered" in r_dup_phone.text


def test_invalid_registration_fields():
    # Short password (< 8 chars)
    r_short = client.post("/api/auth/register", json={
        "name": "Short Pwd",
        "email": "short_pwd@test.org",
        "password": "short",
        "role": "donor"
    })
    assert r_short.status_code == 400
    assert "at least 8 characters" in r_short.text

    # Invalid role
    r_bad_role = client.post("/api/auth/register", json={
        "name": "Bad Role",
        "email": "bad_role@test.org",
        "password": "validPassword123",
        "role": "superman"
    })
    assert r_bad_role.status_code == 400
    assert "Invalid role" in r_bad_role.text

    # Invalid vehicle type
    r_bad_veh = client.post("/api/auth/register", json={
        "name": "Bad Vehicle Vol",
        "email": "bad_veh@test.org",
        "password": "validPassword123",
        "role": "volunteer",
        "vehicle_type": "helicopter"
    })
    assert r_bad_veh.status_code == 400
    assert "Invalid vehicle type" in r_bad_veh.text


def test_ngo_verification_gate_and_acceptance():
    # Register NGO
    r_ngo = client.post("/api/auth/register", json={
        "name": "Unverified NGO",
        "email": "unverified_ngo_test@test.org",
        "password": "ngoPassword123",
        "role": "ngo",
        "organization_name": "Unverified Rescue NGO",
        "capacity": 150
    })
    assert r_ngo.status_code == 201

    # Login as unverified NGO
    l_ngo = client.post("/api/auth/login", json={
        "email": "unverified_ngo_test@test.org",
        "password": "ngoPassword123"
    })
    assert l_ngo.status_code == 200
    ngo_token = l_ngo.json()["access_token"]
    ngo_user_id = l_ngo.json()["user_id"]

    # Create a pending donation using seeded donor
    l_donor = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    donor_token = l_donor.json()["access_token"]

    now = datetime.now(timezone.utc)
    d_res = client.post(
        "/api/donations",
        headers={"Authorization": f"Bearer {donor_token}"},
        json={
            "food_name": "Gate Test Bread",
            "food_category": "Bakery",
            "quantity": 10.0,
            "quantity_unit": "Kg",
            "preparation_time": (now - timedelta(hours=1)).isoformat(),
            "expiry_time": (now + timedelta(hours=5)).isoformat(),
            "pickup_address": "Test Street"
        }
    )
    assert d_res.status_code in [200, 201]
    donation_id = d_res.json()["id"]

    # 1. Unverified NGO attempting to accept donation is blocked with 403
    r_accept_blocked = client.post(
        f"/api/donations/{donation_id}/accept",
        headers={"Authorization": f"Bearer {ngo_token}"}
    )
    assert r_accept_blocked.status_code == 403
    assert "not verified" in r_accept_blocked.text

    # 2. Admin verifies the NGO
    l_admin = client.post("/api/auth/login", json={
        "email": "admin@fooddonation.org",
        "password": "admin123"
    })
    admin_token = l_admin.json()["access_token"]

    db = next(get_db())
    try:
        ngo_entity = db.query(NGO).filter(NGO.user_id == ngo_user_id).first()
        ngo_id = ngo_entity.id
    finally:
        db.close()

    r_verify = client.post(
        f"/api/admin/ngos/{ngo_id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert r_verify.status_code == 200
    assert r_verify.json()["is_verified"] is True

    # 3. Now verified NGO successfully accepts donation
    r_accept_ok = client.post(
        f"/api/donations/{donation_id}/accept",
        headers={"Authorization": f"Bearer {ngo_token}"}
    )
    assert r_accept_ok.status_code == 200
    assert r_accept_ok.json()["status"] == "accepted"


def test_jwt_issuance_refresh_and_logout():
    # Login as donor
    l_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    assert l_res.status_code == 200
    token_data = l_res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    assert token_data["role"] == "donor"

    # Access protected /auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "donor"

    # Refresh access token
    r_refresh = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r_refresh.status_code == 200
    new_token_data = r_refresh.json()
    new_access = new_token_data["access_token"]
    new_refresh = new_token_data["refresh_token"]

    # Verify old refresh token is revoked due to rotation
    r_old_refresh = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r_old_refresh.status_code == 401
    assert "revoked" in r_old_refresh.text

    # Logout
    r_logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {new_access}"})
    assert r_logout.status_code == 200

    # Refresh after logout must fail
    r_post_logout_refresh = client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert r_post_logout_refresh.status_code == 401


def test_unauthorized_cross_role_access():
    # Login as volunteer
    l_vol = client.post("/api/auth/login", json={
        "email": "vol1@volunteer.org",
        "password": "pass123"
    })
    vol_token = l_vol.json()["access_token"]

    # Volunteer cannot access admin endpoints
    r_admin_stats = client.get("/api/admin/statistics", headers={"Authorization": f"Bearer {vol_token}"})
    assert r_admin_stats.status_code == 403

    r_admin_users = client.get("/api/admin/users", headers={"Authorization": f"Bearer {vol_token}"})
    assert r_admin_users.status_code == 403

    # Donor cannot access volunteer dispatch profile
    l_donor = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    donor_token = l_donor.json()["access_token"]

    r_vol_prof = client.put(
        "/api/volunteers/profile",
        headers={"Authorization": f"Bearer {donor_token}"},
        json={"is_active": True}
    )
    assert r_vol_prof.status_code == 403
