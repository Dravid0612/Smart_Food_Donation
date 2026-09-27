import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment, RescueIssueReport, AuditLog

client = TestClient(app)

def _get_token(email: str, role: str = "admin") -> str:
    # Try logging in
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "pass123" if "admin" not in email else "admin123"})
    if login_resp.status_code == 200:
        return login_resp.json()["access_token"]
    # Register if not exists
    reg_resp = client.post("/api/auth/register", json={
        "name": f"Test {role.title()}",
        "email": email,
        "password": "Password123!",
        "role": role
    })
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    return login_resp.json()["access_token"]

def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}

# ── Test 1: Admin Receiving Summary ──────────────────────────────────────────
def test_admin_receiving_summary():
    admin_token = _get_token("admin@fooddonation.org", "admin")
    resp = client.get("/api/admin/receiving/summary", headers=_auth(admin_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "active_rescues" in data
    assert "urgent_rescues" in data
    assert "critical_rescues" in data
    assert "in_transit" in data
    assert "received_today" in data
    assert "distributed_today" in data
    assert "remaining_today" in data
    assert "issues_open" in data
    assert "food_at_risk_meals" in data
    assert "completed_today" in data
    assert isinstance(data["active_rescues"], int)
    assert isinstance(data["received_today"], (int, float))

# ── Test 2: Admin Receiving Queue & Tab Filtering ───────────────────────────
def test_admin_receiving_tab_filters():
    admin_token = _get_token("admin@fooddonation.org", "admin")
    
    # Test ALL tab
    resp_all = client.get("/api/admin/receiving?tab=ALL", headers=_auth(admin_token))
    assert resp_all.status_code == 200
    all_data = resp_all.json()
    assert "items" in all_data
    assert "total" in all_data

    # Test EXPECTED tab
    resp_exp = client.get("/api/admin/receiving?tab=EXPECTED", headers=_auth(admin_token))
    assert resp_exp.status_code == 200
    for item in resp_exp.json()["items"]:
        assert item["status"] in ["accepted", "volunteer_assigned"]

    # Test ARRIVING tab
    resp_arr = client.get("/api/admin/receiving?tab=ARRIVING", headers=_auth(admin_token))
    assert resp_arr.status_code == 200
    for item in resp_arr.json()["items"]:
        assert item["status"] in ["collected", "arrived_at_donor"]

    # Test RECEIVED tab
    resp_rec = client.get("/api/admin/receiving?tab=RECEIVED", headers=_auth(admin_token))
    assert resp_rec.status_code == 200
    for item in resp_rec.json()["items"]:
        assert item["status"] == "delivered"

    # Test COMPLETED tab
    resp_comp = client.get("/api/admin/receiving?tab=COMPLETED", headers=_auth(admin_token))
    assert resp_comp.status_code == 200
    for item in resp_comp.json()["items"]:
        assert item["status"] == "completed"

# ── Test 3: Rescue Detail & 9-Step Linear Timeline ───────────────────────────
def test_admin_rescue_detail_and_timeline():
    admin_token = _get_token("admin@fooddonation.org", "admin")
    
    # Get a donation ID
    resp_list = client.get("/api/admin/receiving?tab=ALL", headers=_auth(admin_token))
    assert resp_list.status_code == 200
    items = resp_list.json()["items"]
    if items:
        did = items[0]["id"]
        resp_detail = client.get(f"/api/admin/rescues/{did}", headers=_auth(admin_token))
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["id"] == did
        assert "timeline" in detail
        assert len(detail["timeline"]) == 9
        stages = [t["stage"] for t in detail["timeline"]]
        assert "DONATION_CREATED" in stages
        assert "AI_ANALYZED" in stages
        assert "NGO_ACCEPTED" in stages
        assert "VOLUNTEER_ASSIGNED" in stages
        assert "PICKUP_VERIFIED" in stages
        assert "IN_TRANSIT" in stages
        assert "FOOD_RECEIVED" in stages
        assert "BENEFICIARY_DISTRIBUTION" in stages
        assert "RESCUE_COMPLETED" in stages

# ── Test 4: NGO Capacity Status ──────────────────────────────────────────────
def test_admin_ngo_capacity_status():
    admin_token = _get_token("admin@fooddonation.org", "admin")
    resp = client.get("/api/admin/ngos/capacity", headers=_auth(admin_token))
    assert resp.status_code == 200
    ngos = resp.json()
    assert isinstance(ngos, list)
    for n in ngos:
        assert "organization_name" in n
        assert "current_capacity" in n
        assert "max_capacity" in n
        assert "utilization_percent" in n
        assert n["status_color"] in ["GREEN", "AMBER", "RED"]

# ── Test 5: Food Category Breakdown ──────────────────────────────────────────
def test_admin_category_breakdown():
    admin_token = _get_token("admin@fooddonation.org", "admin")
    resp = client.get("/api/admin/category-breakdown", headers=_auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_meals" in data
    assert "categories" in data
    assert isinstance(data["categories"], list)

# ── Test 6: Admin Intervention Action & Audit Log ────────────────────────────
def test_admin_intervention_submission():
    admin_token = _get_token("admin@fooddonation.org", "admin")
    donor_token = _get_token("donor_int_test@hotel.com", "donor")
    
    # Create test donation
    now = datetime.now(timezone.utc)
    create_resp = client.post("/api/donations", headers=_auth(donor_token), json={
        "food_name": "Surplus Lunch Packets",
        "food_category": "Cooked Food",
        "quantity": 40.0,
        "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=2)).isoformat(),
        "pickup_address": "Test Hotel, Bangalore",
        "latitude": 12.97,
        "longitude": 77.59
    })
    assert create_resp.status_code == 201
    did = create_resp.json()["id"]

    # Submit valid intervention
    int_resp = client.post("/api/admin/interventions", headers=_auth(admin_token), json={
        "donation_id": did,
        "reason_code": "no_volunteer_available",
        "notes": "Triggering priority broadcast to nearby couriers",
        "action_type": "EMERGENCY_BROADCAST"
    })
    assert int_resp.status_code == 200
    res = int_resp.json()
    assert res["success"] is True
    assert res["donation_id"] == did
    assert res["audit_log_id"] is not None

    # Invalid reason code should fail 400
    bad_resp = client.post("/api/admin/interventions", headers=_auth(admin_token), json={
        "donation_id": did,
        "reason_code": "invalid_reason_123"
    })
    assert bad_resp.status_code == 400

# ── Test 7: RBAC Protection (Non-Admin 403 / 401) ─────────────────────────────
def test_admin_receiving_rbac_protection():
    donor_token = _get_token("donor_rbac_test@hotel.com", "donor")
    vol_token = _get_token("vol_rbac_test@courier.org", "volunteer")

    # Donor access -> 403 Forbidden
    resp_donor = client.get("/api/admin/receiving/summary", headers=_auth(donor_token))
    assert resp_donor.status_code == 403

    # Volunteer access -> 403 Forbidden
    resp_vol = client.get("/api/admin/receiving", headers=_auth(vol_token))
    assert resp_vol.status_code == 403

    # Unauthenticated -> 401 Unauthorized
    resp_unauth = client.get("/api/admin/receiving/summary")
    assert resp_unauth.status_code == 401
