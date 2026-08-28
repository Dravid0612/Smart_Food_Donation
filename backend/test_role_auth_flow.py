import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def run_role_auth_verification():
    print("\n" + "=" * 70)
    print("  ROLE-BASED AUTHENTICATION & LOGIN SYSTEM VERIFICATION")
    print("=" * 70)

    test_accounts = [
        ("Donor (Hotel)", "donor1@hotel.com", "pass123", "donor", "/donor"),
        ("NGO (Charity)", "ngo1@greenhope.org", "pass123", "ngo", "/ngo"),
        ("Volunteer (Rider)", "vol1@volunteer.org", "pass123", "volunteer", "/volunteer"),
        ("Admin (Platform)", "admin@fooddonation.org", "admin123", "admin", "/admin"),
    ]

    tokens = {}

    # 1. Test Unified Login for all 4 roles
    print("\n[TEST 1] Single Common Login -> Authoritative Backend Role Detection")
    for label, email, password, expected_role, expected_route in test_accounts:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"Login failed for {label}: {resp.text}"
        data = resp.json()
        assert data["role"] == expected_role, f"Role mismatch: {data['role']} vs {expected_role}"
        assert "access_token" in data
        tokens[expected_role] = data["access_token"]
        print(f"  [OK] {label:20} -> Email: {email:25} -> Role: {data['role'].upper():10} -> Route: {expected_route}")

    # 2. Test Phone Number Login
    print("\n[TEST 2] Phone Number + Password Login")
    phone_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": "+919811111111", "password": "pass123"})
    assert phone_resp.status_code == 200
    phone_data = phone_resp.json()
    assert phone_data["role"] == "donor"
    print(f"  [OK] Phone Login (+919811111111) -> Authenticated as User ID: {phone_data['user_id']} ({phone_data['name']})")

    # 3. Test Blocked Public Admin Registration
    print("\n[TEST 3] Admin Public Registration Protection")
    admin_reg_resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "name": "Malicious Admin",
            "email": "hacker_admin@domain.com",
            "password": "password123",
            "role": "admin"
        }
    )
    assert admin_reg_resp.status_code == 403
    print(f"  [OK] Public Admin Registration Rejected (HTTP 403): {admin_reg_resp.json()['detail']}")

    # 4. Test Cross-Role Backend Authorization (Strict Permission Isolation)
    print("\n[TEST 4] Cross-Role Backend Permission & Resource Ownership Enforcement")
    
    # 4a. Donor attempting to access Admin Stats
    donor_admin_req = requests.get(
        f"{BASE_URL}/admin/statistics",
        headers={"Authorization": f"Bearer {tokens['donor']}"}
    )
    assert donor_admin_req.status_code == 403
    print(f"  [OK] Donor Accessing Admin Stats: BLOCKED (HTTP 403 Forbidden)")

    # 4b. Volunteer attempting to access Admin Users
    vol_admin_req = requests.get(
        f"{BASE_URL}/admin/users",
        headers={"Authorization": f"Bearer {tokens['volunteer']}"}
    )
    assert vol_admin_req.status_code == 403
    print(f"  [OK] Volunteer Accessing Admin Users: BLOCKED (HTTP 403 Forbidden)")

    # 4c. Donor attempting to verify volunteer OTP
    donor_vol_req = requests.post(
        f"{BASE_URL}/volunteers/verify-otp",
        json={"donation_id": 1, "otp": "999999"},
        headers={"Authorization": f"Bearer {tokens['donor']}"}
    )
    assert donor_vol_req.status_code == 403
    print(f"  [OK] Donor Accessing Volunteer OTP Verify: BLOCKED (HTTP 403 Forbidden)")

    # 4d. Admin accessing Admin Stats
    admin_stats_req = requests.get(
        f"{BASE_URL}/admin/statistics",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert admin_stats_req.status_code == 200
    print(f"  [OK] Admin Accessing Admin Stats: ALLOWED (HTTP 200 OK - Total Users: {admin_stats_req.json()['total_users']})")

    # 5. Test Session Expiration / Invalid Token
    print("\n[TEST 5] Expired / Invalid Token Handling")
    invalid_req = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": "Bearer invalid_expired_jwt_token_sample"}
    )
    assert invalid_req.status_code == 401
    print(f"  [OK] Invalid Token Rejected (HTTP 401 Unauthorized) -> Triggers Flutter Session Expiration")

    print("\n" + "=" * 70)
    print("  ALL 5 ROLE-BASED AUTHENTICATION FLOWS VERIFIED SUCCESSFULLY!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_role_auth_verification()
