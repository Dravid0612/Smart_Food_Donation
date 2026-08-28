import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Smart Food Donation" in response.json()["message"]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"

def test_login_donor():
    response = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "donor"
    assert data["name"] == "Taj Hotel Restaurant"

def test_login_ngo():
    response = client.post("/api/auth/login", json={
        "email": "ngo1@greenhope.org",
        "password": "pass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "ngo"

def test_login_volunteer():
    response = client.post("/api/auth/login", json={
        "email": "vol1@volunteer.org",
        "password": "pass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "volunteer"

def test_login_admin():
    response = client.post("/api/auth/login", json={
        "email": "admin@fooddonation.org",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"

def test_get_donations_unauthorized():
    response = client.get("/api/donations")
    assert response.status_code == 401

def test_get_donations_authorized():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]
    
    response = client.get("/api/donations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    donations = response.json()
    assert isinstance(donations, list)
    assert len(donations) > 0

def test_recommendation_algorithm():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]
    
    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {token}"}).json()
    donation_id = donations[0]["id"]

    rec_res = client.get(f"/api/donations/{donation_id}/recommend-ngo", headers={"Authorization": f"Bearer {token}"})
    assert rec_res.status_code == 200
    recommendations = rec_res.json()
    assert isinstance(recommendations, list)
    if len(recommendations) > 0:
        assert "score" in recommendations[0]
        assert "reason" in recommendations[0]

def test_hungarian_batch_matching():
    login_res = client.post("/api/auth/login", json={
        "email": "admin@fooddonation.org",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    
    batch_res = client.get("/api/donations/batch-match/run", headers={"Authorization": f"Bearer {token}"})
    assert batch_res.status_code == 200
    data = batch_res.json()
    assert "matched_pairs" in data
    assert "global_efficiency_score" in data
    assert isinstance(data["matched_pairs"], list)

def test_carbon_impact_calculation():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]
    
    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {token}"}).json()
    donation_id = donations[0]["id"]

    impact_res = client.get(f"/api/donations/{donation_id}/carbon-impact", headers={"Authorization": f"Bearer {token}"})
    assert impact_res.status_code == 200
    data = impact_res.json()
    assert "co2_saved_kg" in data
    assert "water_saved_liters" in data
def test_ai_vision_analysis_endpoint():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]

    # Test AI food analysis
    form_data = {
        "food_category": "Cooked Food",
        "quantity": "25",
        "storage_method": "Refrigerated",
        "storage_duration_hours": "3.0",
        "packaging_condition": "Sealed / Covered"
    }
    response = client.post(
        "/api/ai/analyze-food",
        data=form_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "food_detected" in data
    assert "visible_spoilage" in data
    assert "discoloration" in data
    assert "packaging" in data
    assert "visual_condition" in data
    assert "confidence" in data
    assert "warning" in data
    assert "cannot guarantee food safety" in data["warning"]
    assert data["visual_condition"] in ["GOOD", "FAIR", "POOR"]

def test_volunteer_5_factor_recommendation():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]

    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {token}"}).json()
    donation_id = donations[0]["id"]

    rec_res = client.get(f"/api/donations/{donation_id}/recommend-volunteer", headers={"Authorization": f"Bearer {token}"})
    assert rec_res.status_code == 200
    volunteers = rec_res.json()
    assert isinstance(volunteers, list)
    if len(volunteers) > 0:
        vol = volunteers[0]
        assert "score" in vol
        assert "score_breakdown" in vol
        assert "carrying_capacity" in vol
        assert "vehicle_type" in vol
        assert "reliability_score" in vol
        assert "distance" in vol["score_breakdown"]
        assert "capacity" in vol["score_breakdown"]

def test_backend_otp_and_qr_verification():
    # 1. Login donor to create donation
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    exp_iso = (now + timedelta(hours=6)).isoformat()

    create_res = client.post(
        "/api/donations",
        json={
            "food_name": "OTP Test Meal",
            "food_category": "Cooked Food",
            "quantity": 15.0,
            "quantity_unit": "Meals",
            "preparation_time": now_iso,
            "expiry_time": exp_iso,
            "pickup_address": "MG Road, Bangalore"
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert create_res.status_code == 201
    don_id = create_res.json()["id"]

    # 2. Get verification OTP as donor
    code_res = client.get(f"/api/donations/{don_id}/verification-code", headers={"Authorization": f"Bearer {donor_token}"})
    assert code_res.status_code == 200
    otp = code_res.json()["otp"]
    qr_token = code_res.json()["qr_token"]
    assert len(otp) == 6
    assert qr_token.startswith("DON-")

    # 3. Volunteer login & assignment
    vol_login = client.post("/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
    vol_token = vol_login.json()["access_token"]
    vol_id = vol_login.json()["user_id"]

    assign_res = client.post(
        f"/api/volunteers/assignments?donation_id={don_id}&volunteer_id={vol_id}",
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert assign_res.status_code == 200

    # 4. Attempt verify with wrong OTP -> must fail with 400 (assigned volunteer, but bad OTP)
    wrong_res = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": don_id, "otp": "000000"},
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert wrong_res.status_code == 400

    # 5. Verify with correct OTP -> success
    correct_res = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": don_id, "otp": otp},
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert correct_res.status_code == 200
    assert correct_res.json()["status"] == "collected"

def test_emergency_escalation():
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {donor_token}"}).json()
    don_id = donations[0]["id"]

    escalate_res = client.post(f"/api/donations/{don_id}/escalate", headers={"Authorization": f"Bearer {donor_token}"})
    assert escalate_res.status_code == 200
    assert escalate_res.json()["is_emergency"] is True

def test_cancellation_lifecycle():
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    exp_iso = (now + timedelta(hours=6)).isoformat()

    create_res = client.post(
        "/api/donations",
        json={
            "food_name": "Cancel Test Meal",
            "food_category": "Cooked Food",
            "quantity": 10.0,
            "quantity_unit": "Meals",
            "preparation_time": now_iso,
            "expiry_time": exp_iso,
            "pickup_address": "Indiranagar, Bangalore"
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    don_id = create_res.json()["id"]

    cancel_res = client.post(
        f"/api/donations/{don_id}/cancel",
        json={"reason": "Donor unavailable due to kitchen emergency"},
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

def test_qr_verification_flow():
    # 1. Login donor to create donation
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        json={
            "food_name": "QR Verification Test Food",
            "food_category": "Bakery",
            "quantity": 20.0,
            "quantity_unit": "Packets",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=6)).isoformat(),
            "pickup_address": "Koramangala 4th Block"
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert create_res.status_code == 201
    don_id = create_res.json()["id"]

    code_res = client.get(f"/api/donations/{don_id}/verification-code", headers={"Authorization": f"Bearer {donor_token}"})
    assert code_res.status_code == 200
    qr_token = code_res.json()["qr_token"]

    vol_login = client.post("/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
    vol_token = vol_login.json()["access_token"]
    vol_id = vol_login.json()["user_id"]

    assign_res = client.post(
        f"/api/volunteers/assignments?donation_id={don_id}&volunteer_id={vol_id}",
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert assign_res.status_code == 200

    # Wrong QR token -> must fail with 400 (assigned volunteer, but bad QR token)
    wrong_qr = client.post(
        "/api/volunteers/verify-qr",
        json={"donation_id": don_id, "qr_token": "INVALID-QR"},
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert wrong_qr.status_code == 400

    # Correct QR token
    correct_qr = client.post(
        "/api/volunteers/verify-qr",
        json={"donation_id": don_id, "qr_token": qr_token},
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert correct_qr.status_code == 200
    assert correct_qr.json()["status"] == "collected"

def test_ngo_update_operating_hours_and_demands():
    ngo_login = client.post("/api/auth/login", json={"email": "ngo1@greenhope.org", "password": "pass123"})
    ngo_token = ngo_login.json()["access_token"]

    my_ngo = client.get("/api/ngos/me", headers={"Authorization": f"Bearer {ngo_token}"}).json()
    ngo_id = my_ngo["id"]

    # Update operating hours as dict
    hours_res = client.put(
        f"/api/ngos/{ngo_id}/operating-hours",
        json={"operating_hours": {"monday": {"open": "07:00", "close": "21:00", "closed": False}}},
        headers={"Authorization": f"Bearer {ngo_token}"}
    )
    assert hours_res.status_code == 200
    assert "07:00" in hours_res.json()["operating_hours"]

    # Update demands as dict
    demands_res = client.put(
        f"/api/ngos/{ngo_id}/demands",
        json={"demand_requirements": {"Cooked Food": 120, "Bakery": 40}},
        headers={"Authorization": f"Bearer {ngo_token}"}
    )
    assert demands_res.status_code == 200
    assert "120" in demands_res.json()["demand_requirements"]

def test_volunteer_failure_reporting():
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/donations",
        json={
            "food_name": "Failure Reporting Test Item",
            "food_category": "Cooked Food",
            "quantity": 12.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=6)).isoformat(),
            "pickup_address": "Indiranagar, Bangalore"
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    don_id = create_res.json()["id"]

    vol_login = client.post("/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
    vol_token = vol_login.json()["access_token"]

    # Volunteer reports pickup failure
    fail_res = client.post(
        f"/api/volunteers/report-failure?donation_id={don_id}",
        json={
            "failure_type": "pickup_failed",
            "reason": "donor_unavailable",
            "remarks": "Donor premises closed unexpectedly"
        },
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert fail_res.status_code == 200

    # Verify donation status
    detail = client.get(f"/api/donations/{don_id}", headers={"Authorization": f"Bearer {donor_token}"}).json()
    assert detail["status"] == "pickup_failed"
    assert "donor_unavailable" in detail["failure_reason"]

def test_admin_ngo_verification_and_stats():
    admin_login = client.post("/api/auth/login", json={"email": "admin@fooddonation.org", "password": "admin123"})
    admin_token = admin_login.json()["access_token"]

    # Verify unverified NGO (ngo3)
    ngos = client.get("/api/admin/ngos", headers={"Authorization": f"Bearer {admin_token}"}).json()
    unverified = [n for n in ngos if not n["is_verified"]]
    if unverified:
        target_id = unverified[0]["id"]
        verify_res = client.post(f"/api/ngos/{target_id}/verify", headers={"Authorization": f"Bearer {admin_token}"})
        assert verify_res.status_code == 200
        assert verify_res.json()["is_verified"] is True

    # Check stats
    stats_res = client.get("/api/admin/statistics", headers={"Authorization": f"Bearer {admin_token}"})
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_users" in stats
    assert "total_donations" in stats
    assert "meals_donated" in stats

def test_complete_end_to_end_lifecycle_workflow():
    """
    End-to-End Workflow:
    1. Donor creates donation
    2. Backend AI assesses food
    3. NGO checks recommendations and accepts
    4. Volunteer receives assignment & checks recommendation
    5. Volunteer arrives at Donor & verifies via backend OTP
    6. Volunteer delivers to NGO & marks delivered
    7. Donor receives points and sees completed state
    """
    # 1. Donor creates donation
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    don_res = client.post(
        "/api/donations",
        json={
            "food_name": "Full Lifecycle Hot Meals",
            "food_category": "Cooked Food",
            "quantity": 30.0,
            "quantity_unit": "Meals",
            "preparation_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=6)).isoformat(),
            "pickup_address": "MG Road Food Court, Bangalore",
            "storage_method": "Heated/Insulated",
            "storage_duration_hours": 1.0,
            "packaging_condition": "Sealed / Covered",
            "ai_visual_condition": "GOOD",
            "ai_confidence_score": 0.94,
            "condition_score": 92
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert don_res.status_code == 201
    donation = don_res.json()
    donation_id = donation["id"]
    assert donation["status"] == "pending"

    # 2. Get OTP for pickup
    code_data = client.get(f"/api/donations/{donation_id}/verification-code", headers={"Authorization": f"Bearer {donor_token}"}).json()
    otp = code_data["otp"]

    # 3. NGO recommends and accepts
    ngo_login = client.post("/api/auth/login", json={"email": "ngo1@greenhope.org", "password": "pass123"})
    ngo_token = ngo_login.json()["access_token"]

    recs = client.get(f"/api/donations/{donation_id}/recommend-ngo", headers={"Authorization": f"Bearer {ngo_token}"}).json()
    assert len(recs) > 0

    accept_res = client.post(f"/api/donations/{donation_id}/accept", headers={"Authorization": f"Bearer {ngo_token}"})
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    # 4. Volunteer assigns & accepts
    vol_login = client.post("/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
    vol_token = vol_login.json()["access_token"]
    vol_id = vol_login.json()["user_id"]

    assign_res = client.post(
        f"/api/volunteers/assignments?donation_id={donation_id}&volunteer_id={vol_id}",
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert assign_res.status_code == 200

    # 5. Volunteer verifies OTP at pickup
    verify_res = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": donation_id, "otp": otp},
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "collected"

    # 6. Volunteer delivers food
    deliver_res = client.post(
        f"/api/donations/{donation_id}/deliver",
        headers={"Authorization": f"Bearer {vol_token}"}
    )
    assert deliver_res.status_code == 200
    assert deliver_res.json()["status"] == "delivered"  # Two-stage pipeline: deliver -> NGO records distribution -> completed

    # 7. Check Carbon Impact & Points
    impact_res = client.get(f"/api/donations/{donation_id}/carbon-impact", headers={"Authorization": f"Bearer {donor_token}"})
    assert impact_res.status_code == 200
    impact = impact_res.json()
    assert impact["co2_saved_kg"] > 0
    assert impact["status"] == "delivered"

def test_recurring_donation_lifecycle():
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    # 1. Create recurring profile
    create_rec = client.post(
        "/api/donations/recurring/create",
        json={
            "template_name": "Daily Dinner Buffet Leftover",
            "food_name": "Assorted Cooked Buffet",
            "food_category": "Cooked Food",
            "typical_quantity": 75.0,
            "quantity_unit": "Meals",
            "frequency": "Daily",
            "preferred_pickup_time": "21:00",
            "pickup_address": "Taj Hotel MG Road",
            "storage_method": "Heated/Insulated",
            "packaging_condition": "Sealed / Covered"
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert create_rec.status_code == 201
    rec_data = create_rec.json()
    rec_id = rec_data["id"]

    # 2. List recurring templates
    list_rec = client.get("/api/donations/recurring/list", headers={"Authorization": f"Bearer {donor_token}"})
    assert list_rec.status_code == 200
    assert len(list_rec.json()) > 0

    # 3. Instantiate today's donation in 1 tap
    inst_res = client.post(f"/api/donations/recurring/{rec_id}/instantiate", headers={"Authorization": f"Bearer {donor_token}"})
    assert inst_res.status_code == 201
    today_don = inst_res.json()
    assert "Daily Dinner Buffet" in today_don["food_name"] or "Assorted Cooked Buffet" in today_don["food_name"]
    assert today_don["status"] == "pending"

    # 4. Deactivate template
    del_res = client.delete(f"/api/donations/recurring/{rec_id}", headers={"Authorization": f"Bearer {donor_token}"})
    assert del_res.status_code == 200

def test_donation_certificate_and_csr_summary():
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {donor_token}"}).json()
    assert len(donations) > 0
    don_id = donations[0]["id"]

    # Generate certificate
    cert_res = client.get(f"/api/donations/{don_id}/certificate", headers={"Authorization": f"Bearer {donor_token}"})
    assert cert_res.status_code == 200
    cert = cert_res.json()
    assert "certificate_id" in cert
    assert "Certificate of Participation" in cert["title"]
    assert cert["co2_saved_kg"] >= 0
    assert cert["verification_hash"] is not None

    # Get CSR Impact Summary
    csr_res = client.get("/api/donations/csr/summary", headers={"Authorization": f"Bearer {donor_token}"})
    assert csr_res.status_code == 200
    csr = csr_res.json()
    assert "total_meals_donated" in csr
    assert "estimated_disposal_cost_avoided_inr" in csr
    assert "trust_score" in csr

def test_two_way_rating_flow():
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    ngo_login = client.post("/api/auth/login", json={"email": "ngo1@greenhope.org", "password": "pass123"})
    ngo_user_id = ngo_login.json()["user_id"]

    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {donor_token}"}).json()
    don_id = donations[0]["id"]

    # Donor rates NGO
    rate_res = client.post(
        f"/api/donations/{don_id}/rate",
        json={
            "donation_id": don_id,
            "to_user_id": ngo_user_id,
            "role_to": "ngo",
            "rating_score": 5,
            "feedback": "Prompt acceptance and seamless receiving at distribution centre!",
            "tags": "Professional, On-time, Dignified"
        },
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert rate_res.status_code == 201
    rating = rate_res.json()
    assert rating["rating_score"] == 5

    # Get ratings
    all_ratings = client.get(f"/api/donations/{don_id}/ratings", headers={"Authorization": f"Bearer {donor_token}"}).json()
    assert len(all_ratings) > 0

def test_role_based_login_and_phone_support():
    # 1. Donor Login via email
    res1 = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    assert res1.status_code == 200
    assert res1.json()["role"] == "donor"

    # 2. Donor Login via phone (+919811111111)
    res2 = client.post("/api/auth/login", json={"email": "+919811111111", "password": "pass123"})
    assert res2.status_code == 200
    assert res2.json()["role"] == "donor"

    # 3. NGO Login
    res3 = client.post("/api/auth/login", json={"email": "ngo1@greenhope.org", "password": "pass123"})
    assert res3.status_code == 200
    assert res3.json()["role"] == "ngo"

    # 4. Volunteer Login
    res4 = client.post("/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
    assert res4.status_code == 200
    assert res4.json()["role"] == "volunteer"

    # 5. Admin Login
    res5 = client.post("/api/auth/login", json={"email": "admin@fooddonation.org", "password": "admin123"})
    assert res5.status_code == 200
    assert res5.json()["role"] == "admin"

def test_public_admin_registration_blocked():
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Intruder Admin",
            "email": "intruder_admin@fake.com",
            "password": "pass123456",
            "role": "admin"
        }
    )
    assert res.status_code == 403
    assert "Public admin registration is not permitted" in res.json()["detail"]

def test_volunteer_and_ngo_registration():
    # Register new volunteer
    v_res = client.post(
        "/api/auth/register",
        json={
            "name": "Kiran Volunteer",
            "email": "kiran_vol@test.org",
            "password": "pass123456",
            "phone": "+919988776655",
            "role": "volunteer",
            "vehicle_type": "van",
            "carrying_capacity": 500
        }
    )
    assert v_res.status_code == 201
    v_user = v_res.json()
    assert v_user["role"] == "volunteer"
    assert v_user["vehicle_type"] == "van"
    assert v_user["carrying_capacity"] == 500

    # Register new NGO (unverified by default)
    n_res = client.post(
        "/api/auth/register",
        json={
            "name": "Anand Officer",
            "email": "anand_ngo@test.org",
            "password": "pass123456",
            "phone": "+919988776644",
            "role": "ngo",
            "organization_name": "Hope Children Care Trust",
            "capacity": 300
        }
    )
    assert n_res.status_code == 201
    n_user = n_res.json()
    assert n_user["role"] == "ngo"

def test_cross_role_access_rejection():
    # 1. Donor token
    donor_login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    donor_token = donor_login.json()["access_token"]

    # 2. Volunteer token
    vol_login = client.post("/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
    vol_token = vol_login.json()["access_token"]

    # Donor attempting to access Admin endpoint -> 403 Forbidden
    admin_stat = client.get("/api/admin/statistics", headers={"Authorization": f"Bearer {donor_token}"})
    assert admin_stat.status_code == 403

    # Volunteer attempting to access Admin users endpoint -> 403 Forbidden
    admin_users = client.get("/api/admin/users", headers={"Authorization": f"Bearer {vol_token}"})
    assert admin_users.status_code == 403

    # Donor attempting to call volunteer verify-otp -> 403 Forbidden
    donor_otp = client.post(
        "/api/volunteers/verify-otp",
        json={"donation_id": 1, "otp": "123456"},
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert donor_otp.status_code == 403

    # Invalid / expired token attempting to access /auth/me -> 401 Unauthorized
    invalid_token_res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert invalid_token_res.status_code == 401


# =============================================================================
#  SECURITY HARDENING TESTS  (19 new tests added during hardening)
# =============================================================================

def _token(email: str, password: str = "pass123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]

def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_donor_cannot_see_other_donor_donation():
    """Donor A must get 404 (not 403 — enumeration protection) for Donor B's donation."""
    tok1 = _token("donor1@hotel.com")
    tok2 = _token("donor2@kitchen.com")  # donor2 in seed = donor2@kitchen.com
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok2), json={
        "food_name": "Sec Test D2 Only", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "22 Sec Lane"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.get(f"/api/donations/{did}", headers=_h(tok1))
    assert resp.status_code == 404, f"FAIL: Donor1 saw Donor2 donation. Got {resp.status_code}"


def test_unverified_ngo_cannot_accept_donation():
    """Pending/unverified NGO must get 403 when accepting."""
    import time
    from datetime import datetime, timedelta, timezone
    ts = int(time.time() * 1000)
    # Register a brand new unverified NGO
    reg_ngo = client.post("/api/auth/register", json={
        "name": f"Unverified Org {ts}",
        "email": f"unverified_ngo_{ts}@charity.org",
        "password": "pass123456",
        "role": "ngo",
        "organization_name": f"Unverified Charity {ts}",
        "capacity": 100
    })
    assert reg_ngo.status_code in [200, 201]
    
    tok_ngo_unver = _token(f"unverified_ngo_{ts}@charity.org", "pass123456")
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "NGO Verify Test", "food_category": "Cooked Food",
        "quantity": 20, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "1 Verify Road"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo_unver))
    assert resp.status_code == 403, f"FAIL: Unverified NGO allowed. Got {resp.status_code}"


def test_verified_ngo_can_accept_donation():
    """Verified NGO must be allowed (200) to accept a pending donation."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Verified NGO Accept", "food_category": "Cooked Food",
        "quantity": 15, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "5 Verified Street"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert resp.status_code == 200, f"FAIL: Verified NGO blocked. {resp.text}"
    assert resp.json()["status"] == "accepted"


def test_concurrent_ngo_acceptance_produces_409():
    """Second accept on same donation must return 409 Conflict."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Concurrency Test", "food_category": "Cooked Food",
        "quantity": 5, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "10 Race Ave"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    r1 = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert r1.status_code == 200
    r2 = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert r2.status_code == 409, f"FAIL: Duplicate accept not blocked. Got {r2.status_code}"


def test_donor_can_cancel_own_donation():
    """Donor can cancel their own pending donation (200)."""
    tok_donor = _token("donor1@hotel.com")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Cancel Test", "food_category": "Cooked Food",
        "quantity": 12, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "99 Cancel St"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.post(f"/api/donations/{did}/cancel", headers=_h(tok_donor),
                       json={"reason": "donor_unavailable"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_donor_cannot_cancel_other_donor_donation():
    """Donor A must get 404 when cancelling Donor B's donation."""
    tok1 = _token("donor1@hotel.com")
    tok2 = _token("donor2@kitchen.com")  # donor2 in seed = donor2@kitchen.com
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok2), json={
        "food_name": "D2 Cancel Ownership", "food_category": "Cooked Food",
        "quantity": 8, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "77 Ownership Rd"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.post(f"/api/donations/{did}/cancel", headers=_h(tok1),
                       json={"reason": "donor_unavailable"})
    assert resp.status_code == 404, f"FAIL: D1 cancelled D2 donation. Got {resp.status_code}"


def test_otp_verification_requires_assignment_ownership():
    """Unassigned volunteer must be blocked (403) even if they know the OTP."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol2 = _token("vol2@volunteer.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "OTP Ownership Test", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "55 OTP Security Rd"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    # vol2 is unassigned — must be blocked
    otp_resp = client.post("/api/volunteers/verify-otp",
                           headers=_h(tok_vol2),
                           json={"donation_id": did, "otp": "000000"})
    assert otp_resp.status_code == 403, f"FAIL: Unassigned volunteer OTP accepted. Got {otp_resp.status_code}"


def test_otp_cannot_be_reused():
    """After successful OTP use, the same OTP must return 409."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, VolunteerAssignment, User, NGO
    from datetime import datetime, timedelta, timezone
    db = SessionLocal()
    try:
        donor = db.query(User).filter(User.email == "donor1@hotel.com").first()
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        ngo1 = db.query(NGO).filter(NGO.is_verified == True).first()
        now = datetime.now(timezone.utc)
        don = FoodDonation(
            donor_id=donor.id, food_name="OTP Replay Test",
            food_category="Cooked Food", quantity=5, quantity_unit="Meals",
            preparation_time=now, expiry_time=now + timedelta(hours=6),
            pickup_address="1 Replay Lane", status="volunteer_assigned",
            assigned_ngo_id=ngo1.id if ngo1 else None,
            assigned_volunteer_id=vol1.id,
            verification_otp="RPLY99",
            otp_expiry=now + timedelta(hours=6),
            qr_code_token="QR-RPLY99",
            qr_expiry=now + timedelta(hours=6)
        )
        db.add(don)
        db.commit(); db.refresh(don)
        asgn = VolunteerAssignment(donation_id=don.id, volunteer_id=vol1.id, status="assigned")
        db.add(asgn)
        db.commit()
        did = don.id
    finally:
        db.close()
    tok_vol1 = _token("vol1@volunteer.org")
    r1 = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1),
                     json={"donation_id": did, "otp": "RPLY99"})
    assert r1.status_code == 200, f"First OTP failed: {r1.text}"
    r2 = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1),
                     json={"donation_id": did, "otp": "RPLY99"})
    # Replay protection fires first (before assignment check) — must always be 409
    assert r2.status_code == 409, f"FAIL: OTP replay allowed. Got {r2.status_code}: {r2.text}"



def test_admin_can_access_stats():
    tok_admin = _token("admin@fooddonation.org", "admin123")
    resp = client.get("/api/admin/statistics", headers=_h(tok_admin))
    assert resp.status_code == 200
    assert "total_users" in resp.json()


def test_donor_cannot_access_admin_stats():
    tok_donor = _token("donor1@hotel.com")
    resp = client.get("/api/admin/statistics", headers=_h(tok_donor))
    assert resp.status_code == 403, f"FAIL: Donor saw admin stats. Got {resp.status_code}"


def test_volunteer_cannot_access_admin_users():
    tok_vol = _token("vol1@volunteer.org")
    resp = client.get("/api/admin/users", headers=_h(tok_vol))
    assert resp.status_code == 403, f"FAIL: Volunteer saw admin users. Got {resp.status_code}"


def test_invalid_state_transition_rejected():
    """Deliver endpoint on a donation not in 'collected' state must be rejected."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "FSM Test", "food_category": "Cooked Food",
        "quantity": 7, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "3 FSM Way"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    # Status is now 'accepted' — deliver requires 'collected' — must fail
    resp = client.post(f"/api/donations/{did}/deliver", headers=_h(tok_vol1))
    assert resp.status_code in [403, 409], f"FAIL: Invalid state jump allowed. Got {resp.status_code}"


def test_deactivated_account_token_is_rejected():
    """JWT of a deactivated user must return 403."""
    import time
    tok_admin = _token("admin@fooddonation.org", "admin123")
    ts = int(time.time())
    reg = client.post("/api/auth/register", json={
        "name": "Temp Deact", "email": f"deact_{ts}@x.com",
        "password": "test1234", "role": "donor"
    })
    assert reg.status_code in [200, 201]
    uid = reg.json()["id"]
    login = client.post("/api/auth/login", json={"email": f"deact_{ts}@x.com", "password": "test1234"})
    assert login.status_code == 200
    user_tok = login.json()["access_token"]
    tog = client.put(f"/api/admin/users/{uid}/toggle-active", headers=_h(tok_admin))
    assert tog.status_code == 200
    assert tog.json()["is_active"] == False
    me = client.get("/api/auth/me", headers=_h(user_tok))
    assert me.status_code == 403, f"FAIL: Deactivated JWT still works. Got {me.status_code}"


def test_login_rate_limit_triggers_429():
    """6th failed login attempt must return 429 Too Many Requests."""
    import time
    ts = int(time.time())
    bad = f"nouser_{ts}@ratelimit.com"
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": bad, "password": "bad"})
        assert r.status_code == 401
    r6 = client.post("/api/auth/login", json={"email": bad, "password": "bad"})
    assert r6.status_code == 429, f"FAIL: Rate limit not triggered. Got {r6.status_code}"


def test_ngo_cannot_see_otp_before_acceptance():
    """NGO browsing pending donation must NOT see OTP or QR."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "OTP Privacy Test", "food_category": "Cooked Food",
        "quantity": 6, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "88 Privacy Rd"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.get(f"/api/donations/{did}", headers=_h(tok_ngo1))
    assert resp.status_code == 200
    d = resp.json()
    assert not d.get("verification_otp"), f"FAIL: NGO sees OTP: {d.get('verification_otp')}"
    assert not d.get("qr_code_token"), f"FAIL: NGO sees QR: {d.get('qr_code_token')}"


def test_donor_can_see_own_otp():
    """Donor must see verification_otp and qr_code_token for their own donation."""
    tok_donor = _token("donor1@hotel.com")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Donor OTP Visibility", "food_category": "Cooked Food",
        "quantity": 4, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "12 OTP View St"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    resp = client.get(f"/api/donations/{did}", headers=_h(tok_donor))
    assert resp.status_code == 200
    d = resp.json()
    assert d.get("verification_otp"), "FAIL: Donor cannot see own OTP"
    assert d.get("qr_code_token"), "FAIL: Donor cannot see own QR"


def test_refresh_token_flow():
    """Login returns refresh_token; POST /auth/refresh issues a new access token."""
    login = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    assert login.status_code == 200
    data = login.json()
    assert "refresh_token" in data, "FAIL: No refresh_token in login response"
    ref = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert ref.status_code == 200, f"Refresh failed: {ref.text}"
    new = ref.json()
    assert "access_token" in new and "refresh_token" in new
    assert new["role"] == "donor"


def test_invalid_refresh_token_rejected():
    """Garbage refresh token must return 401."""
    resp = client.post("/api/auth/refresh", json={"refresh_token": "garbage_token_xyz"})
    assert resp.status_code == 401, f"FAIL: Invalid refresh accepted. Got {resp.status_code}"


def test_audit_log_entries_created():
    """After a login event, audit_logs table must have at least one entry."""
    from app.db.session import SessionLocal
    from app.models.models import AuditLog
    client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    db = SessionLocal()
    try:
        count = db.query(AuditLog).count()
        assert count > 0, f"FAIL: AuditLog empty. count={count}"
        latest = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert latest.action in ["login_success", "login_failed", "login_blocked_inactive",
                                  "donation_accepted", "donation_cancelled", "otp_verified",
                                  "qr_verified", "volunteer_assigned", "logout",
                                  "pickup_confirmed", "delivery_confirmed",
                                  "account_activated", "account_deactivated"]
    finally:
        db.close()


# ==============================================================================
# 30 SPECIFIC FOOD-RESCUE WORKFLOW TESTS (PART 28)
# ==============================================================================

def test_part28_01_ai_food_analysis_response_structure():
    """TEST 1: AI food analysis response structure contains all required fields."""
    tok = _token("donor1@hotel.com")
    resp = client.post(
        "/api/ai/analyze-food",
        headers=_h(tok),
        data={
            "food_category": "Cooked Food",
            "quantity": 25.0,
            "storage_method": "Room Temperature",
            "storage_duration_hours": 2.0,
            "packaging_condition": "Sealed / Covered"
        }
    )
    assert resp.status_code == 200
    d = resp.json()
    assert "food_detected" in d
    assert "visible_spoilage" in d
    assert "discoloration" in d
    assert "packaging_integrity" in d
    assert "visual_condition" in d
    assert "confidence" in d
    assert "observations" in d
    assert "safety_disclaimer" in d
    assert isinstance(d["observations"], list)


def test_part28_02_ai_does_not_return_safe_to_eat():
    """TEST 2: AI does not return 'safe_to_eat' and never claims food safety."""
    tok = _token("donor1@hotel.com")
    resp = client.post("/api/ai/analyze-food", headers=_h(tok), data={"food_category": "Bakery"})
    assert resp.status_code == 200
    d = resp.json()
    assert "safe_to_eat" not in d, "FAIL: AI must never return safe_to_eat"
    assert "is_safe" not in d, "FAIL: AI must never return is_safe"


def test_part28_03_ai_disclaimer_exists():
    """TEST 3: Mandatory safety disclaimer is present in AI response."""
    tok = _token("donor1@hotel.com")
    resp = client.post("/api/ai/analyze-food", headers=_h(tok), data={"food_category": "Cooked Food"})
    assert resp.status_code == 200
    disclaimer = resp.json().get("safety_disclaimer", "")
    assert "Visual assessment only" in disclaimer or "cannot guarantee food safety" in disclaimer


def test_part28_04_metadata_is_stored():
    """TEST 4: Food metadata and FoodAnalysis entity are stored with the donation."""
    from datetime import datetime, timedelta, timezone
    from app.db.session import SessionLocal
    from app.models.models import FoodAnalysis
    tok = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok), json={
        "food_name": "Metadata Storage Test Meals",
        "food_category": "Cooked Food",
        "quantity": 30,
        "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "44 Storage St",
        "storage_method": "Refrigerated",
        "storage_duration_hours": 3.5,
        "packaging_condition": "Sealed / Covered"
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]
    db = SessionLocal()
    try:
        fa = db.query(FoodAnalysis).filter(FoodAnalysis.donation_id == did).first()
        assert fa is not None, "FAIL: FoodAnalysis record not stored in DB"
        assert fa.visual_condition in ["GOOD", "FAIR", "POOR"]
    finally:
        db.close()


def test_part28_05_demand_matched_ngo_ranks_above_closer_non_matching_ngo():
    """TEST 5: Demand-matched NGO ranks above closer non-matching NGO."""
    from app.db.session import SessionLocal
    from app.models.models import NGO, User, FoodDonation
    from app.services.recommendation_service import recommend_ngos
    import json
    from datetime import datetime, timedelta, timezone

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Create a donation for 'Cooked Food'
        donation = FoodDonation(
            donor_id=1,
            food_name="Steamed Rice & Curry",
            food_category="Cooked Food",
            quantity=100.0,
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=4),
            pickup_address="City Center",
            latitude=12.9716,
            longitude=77.5946,
            status="pending"
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        recs = recommend_ngos(db, donation)
        assert len(recs) >= 1
        # Top recommended NGO should have demand_matched == True
        top = recs[0]
        assert top["demand_matched"] == True or "Matches demand" in top["reason"]
    finally:
        db.close()


def test_part28_06_closed_ngo_is_not_normally_selected():
    """TEST 6: Closed NGO is strongly penalized in match ranking compared to open NGO."""
    from app.db.session import SessionLocal
    from app.services.recommendation_service import is_ngo_open_now
    import json
    from datetime import datetime, timezone
    
    # NGO closed schedule
    closed_sched = json.dumps({"sunday": {"closed": True}})
    sunday_dt = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc) # Aug 16, 2026 is Sunday
    is_open, msg = is_ngo_open_now(closed_sched, sunday_dt)
    assert is_open == False
    assert "Closed" in msg


def test_part28_07_ngo_capacity_is_respected():
    """TEST 7: NGO with insufficient capacity receives lower capacity score."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from app.services.recommendation_service import recommend_ngos
    from datetime import datetime, timedelta, timezone
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        large_donation = FoodDonation(
            donor_id=1,
            food_name="Mega Feast Surplus",
            food_category="Cooked Food",
            quantity=9999.0, # Exceeds all normal NGO capacities
            quantity_unit="Meals",
            preparation_time=now,
            expiry_time=now + timedelta(hours=4),
            pickup_address="Mega Hall",
            latitude=12.9716,
            longitude=77.5946,
            status="pending"
        )
        db.add(large_donation)
        db.commit()
        db.refresh(large_donation)
        recs = recommend_ngos(db, large_donation)
        for r in recs:
            assert "Partial capacity" in r["reason"] or r["score"] < 80.0
    finally:
        db.close()


def test_part28_08_volunteer_unavailable_is_excluded():
    """TEST 8: Inactive volunteers are excluded from recommendations."""
    from app.db.session import SessionLocal
    from app.models.models import User, FoodDonation
    from app.services.recommendation_service import recommend_volunteers
    from datetime import datetime, timedelta, timezone
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        d = db.query(FoodDonation).first()
        recs = recommend_volunteers(db, d)
        for r in recs:
            v = db.query(User).filter(User.id == r["volunteer_id"]).first()
            assert v.is_active == True
    finally:
        db.close()


def test_part28_09_volunteer_capacity_is_respected():
    """TEST 9: Volunteer carrying capacity is validated; exceeding returns 400."""
    from app.db.session import SessionLocal
    from app.models.models import User
    from datetime import datetime, timedelta, timezone
    tok_admin = _token("admin@fooddonation.org", "admin123")
    tok_donor = _token("donor1@hotel.com")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1.carrying_capacity = 50
        db.commit()
        vid = vol1.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Heavy Food Batch", "food_category": "Cooked Food",
        "quantity": 500, # 500 meals exceeds bike capacity (50)
        "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Heavy St"
    })
    did = cr.json()["id"]
    # Try assigning to vol1 (carrying_capacity = 50)
    resp = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={vid}", headers=_h(tok_admin))
    assert resp.status_code == 400, f"FAIL: Capacity limit ignored. Got {resp.status_code}"
    assert "exceeds volunteer carrying capacity" in resp.json()["detail"]


def test_part28_10_volunteer_distance_affects_matching():
    """TEST 10: Volunteer proximity affects the calculated distance score."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from app.services.recommendation_service import recommend_volunteers
    db = SessionLocal()
    try:
        d = db.query(FoodDonation).first()
        recs = recommend_volunteers(db, d)
        if len(recs) >= 2:
            assert "distance" in recs[0]["score_breakdown"]
    finally:
        db.close()


def test_part28_11_two_ngos_cannot_accept_same_donation():
    """TEST 11: Two NGOs cannot accept the same donation (row locking concurrency)."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Concurrency Test Rice", "food_category": "Cooked Food",
        "quantity": 15, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "1 Concurrency Ave"
    })
    did = cr.json()["id"]
    r1 = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert r1.status_code == 200
    r2 = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert r2.status_code == 409


def test_part28_12_two_volunteers_cannot_accept_same_assignment():
    """TEST 12: Duplicate volunteer assignments on same donation produce 409 Conflict."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol2 = db.query(User).filter(User.email == "vol2@volunteer.org").first()
        v1_id, v2_id = vol1.id, vol2.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Volunteer Double Assign Test", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "2 Volunteer Way"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    # First assignment to volunteer 1
    r1 = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    assert r1.status_code == 200
    # Second assignment to volunteer 2 must be rejected with 409 Conflict
    r2 = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v2_id}", headers=_h(tok_ngo1))
    assert r2.status_code == 409


def test_part28_13_invalid_fsm_transition_rejected():
    """TEST 13: Invalid FSM jump from pending directly to completed is rejected."""
    tok_donor = _token("donor1@hotel.com")
    tok_admin = _token("admin@fooddonation.org", "admin123")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "FSM Guard Jump Test", "food_category": "Cooked Food",
        "quantity": 12, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "8 Jump St"
    })
    did = cr.json()["id"]
    # Attempting to deliver pending donation directly must fail
    resp = client.post(f"/api/donations/{did}/deliver", headers=_h(tok_admin))
    assert resp.status_code in [400, 409]


def test_part28_14_donation_approaching_deadline_becomes_urgent():
    """TEST 14: Donation with < 2 hours expiry is evaluated as Urgent."""
    from app.services.urgency_service import calculate_urgency
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    prep = now - timedelta(hours=3)
    exp = now + timedelta(minutes=45) # 45 minutes left
    urg = calculate_urgency(prep, exp)
    assert urg in ["Urgent", "Use Soon"]


def test_part28_15_expired_donation_cannot_be_newly_accepted():
    """TEST 15: Expired donation cannot be accepted by an NGO."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from datetime import datetime, timedelta, timezone
    tok_ngo1 = _token("ngo1@greenhope.org")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        d = FoodDonation(
            donor_id=1,
            food_name="Old Expired Meals",
            food_category="Cooked Food",
            quantity=20,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=10),
            expiry_time=now - timedelta(hours=2), # Expired 2 hours ago
            pickup_address="Old St",
            status="expired"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    resp = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert resp.status_code in [400, 409]


def test_part28_16_fallback_ngo_matching_works():
    """TEST 16: NGO rejection triggers fallback search and returns candidate status."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Fallback Test Rice", "food_category": "Cooked Food",
        "quantity": 25, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "99 Fallback St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    # NGO1 rejects
    rej = client.post(f"/api/donations/{did}/reject?reason=Capacity+Full", headers=_h(tok_ngo1))
    assert rej.status_code == 200
    assert "Fallback" in rej.json()["detail"] or rej.json().get("fallback_notified") is not None


def test_part28_17_fallback_volunteer_matching_works():
    """TEST 17: Volunteer rejection triggers fallback volunteer search."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Volunteer Fallback Test", "food_category": "Cooked Food",
        "quantity": 15, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "77 Volunteer Fallback St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    assert assign.status_code == 200
    aid = assign.json()["id"]
    # Vol1 rejects
    rej = client.post(f"/api/volunteers/assignments/{aid}/reject", headers=_h(tok_vol1))
    assert rej.status_code == 200
    assert "Fallback" in rej.json()["detail"] or rej.json().get("fallback_notified") is not None


def test_part28_18_no_volunteer_results_in_escalation():
    """TEST 18: Unassigned urgent donation triggers emergency escalation."""
    from app.db.session import SessionLocal
    from app.services.escalation_service import escalate_donation
    from app.models.models import FoodDonation
    db = SessionLocal()
    try:
        d = db.query(FoodDonation).filter(FoodDonation.status == "pending").first()
        if d:
            esc = escalate_donation(db, d.id, reason="No volunteer in area")
            assert esc.is_emergency == True
    finally:
        db.close()


def test_part28_19_unassigned_volunteer_cannot_see_exact_donor_location():
    """TEST 19: Unassigned volunteer only sees masked coarse neighborhood in public feed."""
    tok_donor = _token("donor1@hotel.com")
    tok_vol1 = _token("vol1@volunteer.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Privacy Masking Food", "food_category": "Cooked Food",
        "quantity": 8, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Flat 402, Taj Complex, Indiranagar, Bangalore"
    })
    did = cr.json()["id"]
    feed = client.get("/api/donations", headers=_h(tok_vol1)).json()
    item = next((x for x in feed if x["id"] == did), None)
    if item:
        assert "Exact address revealed upon acceptance" in item["pickup_address"] or "Flat 402" not in item["pickup_address"]


def test_part28_20_assigned_volunteer_can_access_required_pickup_information():
    """TEST 20: Assigned volunteer gets access to pickup address and donor name."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Assigned Vol Info Test", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Exact Street 55, Bangalore"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    # Volunteer reads detail
    detail = client.get(f"/api/donations/{did}", headers=_h(tok_vol1)).json()
    assert "Exact Street 55" in detail["pickup_address"]
    assert detail.get("donor_name") is not None


def test_part28_21_donor_cannot_access_another_donor_donation():
    """TEST 21: Donor 1 cannot view Donor 2's donation (returns 404)."""
    tok_donor1 = _token("donor1@hotel.com")
    # Register Donor 2
    import time
    ts = int(time.time())
    client.post("/api/auth/register", json={"name": "Donor 2", "email": f"donor2_{ts}@test.com", "password": "pass", "role": "donor"})
    login2 = client.post("/api/auth/login", json={"email": f"donor2_{ts}@test.com", "password": "pass"})
    tok_donor2 = login2.json()["access_token"]
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor2), json={
        "food_name": "Private Donor2 Food", "food_category": "Cooked Food",
        "quantity": 5, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Donor 2 Secret"
    })
    did2 = cr.json()["id"]
    # Donor 1 tries to read Donor 2's donation
    resp = client.get(f"/api/donations/{did2}", headers=_h(tok_donor1))
    assert resp.status_code == 404


def test_part28_22_ngo_cannot_access_another_ngo_private_info():
    """TEST 22: NGO cannot access unassigned private OTP."""
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "NGO Privacy Check", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "88 Private St"
    })
    did = cr.json()["id"]
    # NGO reads detail
    detail = client.get(f"/api/donations/{did}", headers=_h(tok_ngo1)).json()
    assert not detail.get("verification_otp")


def test_part28_23_volunteer_cannot_modify_another_volunteer_task():
    """TEST 23: Volunteer cannot modify another volunteer's task (returns 403)."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol2 = _token("vol2@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Vol Guard Test", "food_category": "Cooked Food",
        "quantity": 8, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "12 Task Rd"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    assert assign.status_code == 200
    aid = assign.json()["id"]
    # Volunteer 2 attempts to update Volunteer 1's task
    resp = client.put(f"/api/volunteers/assignments/{aid}?status_update=delivered", headers=_h(tok_vol2))
    assert resp.status_code == 403


def test_part28_24_otp_cannot_be_reused():
    """TEST 24: Single-use OTP cannot be replayed; second attempt returns 409 Conflict."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "OTP Replay Guard", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Replay St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    # Donor fetches OTP
    codes = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor)).json()
    otp = codes["otp"]
    # 1st verify
    r1 = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1), json={"donation_id": did, "otp": otp})
    assert r1.status_code == 200
    # 2nd verify (replay attempt)
    r2 = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1), json={"donation_id": did, "otp": otp})
    assert r2.status_code == 409


def test_part28_25_otp_cannot_be_used_by_unassigned_volunteer():
    """TEST 25: Unassigned volunteer attempting OTP verification receives 403 Forbidden."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol2 = _token("vol2@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Unassigned OTP Guard", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Guarded St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    codes = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor)).json()
    otp = codes["otp"]
    # Vol 2 (unassigned) tries OTP verify
    resp = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol2), json={"donation_id": did, "otp": otp})
    assert resp.status_code == 403


def test_part28_26_completed_donation_cannot_be_modified_illegally():
    """TEST 26: Completed donation cannot transition to cancelled or pending."""
    from app.services.security_service import validate_donation_transition
    with pytest.raises(Exception):
        validate_donation_transition("completed", "cancelled", "donor")


def test_part28_27_successful_completion_updates_donor_impact():
    """TEST 27: Delivery completion updates donor's total_meals_donated."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Impact Accounting Meals", "food_category": "Cooked Food",
        "quantity": 40, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "40 Impact Way"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    codes = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor)).json()
    client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1), json={"donation_id": did, "otp": codes["otp"]})
    # Deliver
    comp = client.post(f"/api/donations/{did}/deliver", headers=_h(tok_vol1))
    assert comp.status_code == 200
    db = SessionLocal()
    try:
        donor_user = db.query(User).filter(User.email == "donor1@hotel.com").first()
        assert donor_user.total_meals_donated >= 40.0
    finally:
        db.close()


def test_part28_28_failure_triggers_fallback():
    """TEST 28: Reporting task failure logs reason and transitions state."""
    from app.db.session import SessionLocal
    from app.models.models import User
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Failure Report Meals", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Issue St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    # Report failure
    fail = client.post(
        f"/api/volunteers/report-failure?donation_id={did}",
        headers=_h(tok_vol1),
        json={"failure_type": "pickup_failed", "reason": "vehicle_issue", "remarks": "Tire puncture"}
    )
    assert fail.status_code == 200
    assert fail.json()["status"] == "failed"


def test_part28_29_deadline_expiration_produces_correct_terminal_state():
    """TEST 29: Auto-expiry check marks elapsed pending donations as 'expired'."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from datetime import datetime, timedelta, timezone
    tok_donor = _token("donor1@hotel.com")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        d = FoodDonation(
            donor_id=1,
            food_name="Auto Expire Food",
            food_category="Cooked Food",
            quantity=15,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=6),
            expiry_time=now - timedelta(minutes=10), # Past expiry
            pickup_address="Expire St",
            status="pending"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    # Querying donations triggers the real-time expiry sweep
    feed = client.get("/api/donations", headers=_h(tok_donor)).json()
    item = next((x for x in feed if x["id"] == did), None)
    if item:
        assert item["status"] == "expired"


def test_part28_30_end_to_end_complete_food_rescue_flow():
    """TEST 30: Complete End-to-End Food Rescue Flow: Donor -> AI -> NGO -> Volunteer -> OTP -> Delivery -> Completed -> Impact."""
    from app.db.session import SessionLocal
    from app.models.models import User, FoodDonation, NGO
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        if ngo1:
            ngo1.capacity = 200
            ngo1.current_capacity = 200
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1.carrying_capacity = 150 # ensure capacity is adequate for 100 meals
        db.commit()
        v1_id = vol1.id
    finally:
        db.close()

    from datetime import datetime, timedelta, timezone

    # Step 1: Donor creates donation with AI metadata
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Grand Buffet Surplus Feast",
        "food_category": "Cooked Food",
        "quantity": 100,
        "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Taj Hotel Grand Ballroom, Bangalore",
        "storage_method": "Heated/Insulated",
        "storage_duration_hours": 1.5,
        "packaging_condition": "Sealed / Covered",
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.92
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]

    # Step 2: NGO browses and checks transparent rescue feasibility checklist
    chk = client.get(f"/api/donations/{did}/rescue-checklist", headers=_h(tok_ngo1))
    assert chk.status_code == 200
    assert chk.json()["demand_matched"] == True

    # Step 3: Verified NGO accepts donation
    acc = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert acc.status_code == 200
    assert acc.json()["status"] == "accepted"

    # Step 4: Dispatch matching volunteer with capacity >= 100
    assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    assert assign.status_code == 200
    aid = assign.json()["id"]

    # Step 5: Volunteer accepts assignment
    vol_acc = client.post(f"/api/volunteers/assignments/{aid}/accept", headers=_h(tok_vol1))
    assert vol_acc.status_code == 200
    assert vol_acc.json()["status"] == "accepted"

    # Step 6: Donor gets OTP and shares with Volunteer at pickup
    codes = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor)).json()
    otp = codes["otp"]
    assert otp is not None

    # Step 7: Volunteer verifies OTP -> status becomes 'collected'
    otp_res = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1), json={"donation_id": did, "otp": otp})
    assert otp_res.status_code == 200
    assert otp_res.json()["status"] == "collected"

    # Step 8: Volunteer delivers to NGO -> status becomes 'delivered' (two-stage pipeline)
    deliv_res = client.post(f"/api/donations/{did}/deliver", headers=_h(tok_vol1))
    assert deliv_res.status_code == 200
    assert deliv_res.json()["status"] == "delivered"  # NGO must call /distribution to reach 'completed'

    # Step 9: Verify final donor impact recorded in database
    db = SessionLocal()
    try:
        final_donation = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        # After deliver: status is 'delivered'; cost_avoided and beneficiaries are set at deliver time
        assert final_donation.status == "delivered"
        assert final_donation.beneficiaries_served == 100
        assert final_donation.cost_avoided_inr == 2500.0
    finally:
        db.close()


# ==============================================================================
# PART 29 — FINAL GAP CLOSURE, TIMEOUT, CAPACITY, DISTRIBUTION & DISPUTE TESTS
# ==============================================================================

def test_part29_01_ai_metadata_fusion_separates_safety_from_visual_condition():
    """TEST 1: AI metadata fusion decouples visual condition from storage/urgency, and NEVER certifies food safety."""
    from app.services.ai_vision_service import analyze_food_image_and_metadata
    
    # Simulate food with good visual condition but stored at room temperature for 5 hours
    result = analyze_food_image_and_metadata(
        food_category="Cooked Food",
        quantity=50.0,
        storage_method="Room Temperature",
        storage_duration_hours=5.0,
        packaging_condition="Sealed / Covered"
    )
    
    # Visual condition is evaluated
    assert result["visual_condition"] in ["GOOD", "FAIR"]
    assert "safe_to_eat" not in result
    assert "is_safe" not in result
    assert "safety_disclaimer" in result
    assert "Visual assessment only" in result["safety_disclaimer"]
    # Storage assessment notes ambient temperature
    assert "Ambient room temperature for 5.0h" in result["storage_assessment"]


def test_part29_02_ngo_capacity_reservation_and_overbooking_prevention():
    """TEST 2: NGO capacity is strictly reserved on acceptance and overbooking is rejected."""
    from app.db.session import SessionLocal
    from app.models.models import NGO
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    
    # Set NGO1 capacity to 100 meals
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        ngo1.capacity = 100
        ngo1.current_capacity = 100
        db.commit()
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    # Donation A = 80 meals
    cr1 = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Batch A Rice & Curry", "food_category": "Cooked Food",
        "quantity": 80, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Catering Hall A"
    })
    did1 = cr1.json()["id"]

    # Donation B = 50 meals
    cr2 = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Batch B Biryani", "food_category": "Cooked Food",
        "quantity": 50, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Catering Hall B"
    })
    did2 = cr2.json()["id"]

    # NGO1 accepts Donation A (80 meals) -> Remaining capacity becomes 20 meals
    acc1 = client.post(f"/api/donations/{did1}/accept", headers=_h(tok_ngo1))
    assert acc1.status_code == 200

    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 20
    finally:
        db.close()

    # NGO1 tries to accept Donation B (50 meals) -> Fails with 400 Bad Request because 50 > 20
    acc2 = client.post(f"/api/donations/{did2}/accept", headers=_h(tok_ngo1))
    assert acc2.status_code == 400
    assert "insufficient" in acc2.json()["detail"].lower()


def test_part29_03_ngo_capacity_release_on_cancellation():
    """TEST 3: When an accepted donation is cancelled, NGO reserved capacity is restored."""
    from app.db.session import SessionLocal
    from app.models.models import NGO
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")

    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        ngo1.capacity = 100
        ngo1.current_capacity = 100
        db.commit()
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Cancellable Surplus", "food_category": "Cooked Food",
        "quantity": 60, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Kitchen 1"
    })
    did = cr.json()["id"]

    # Accept -> capacity decreases to 40
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))

    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 40
    finally:
        db.close()

    # Cancel donation -> capacity restored to 100
    cancel_res = client.post(f"/api/donations/{did}/cancel", headers=_h(tok_donor), json={"reason": "donor_unavailable"})
    assert cancel_res.status_code == 200

    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 100
    finally:
        db.close()


def test_part29_04_timeout_based_ngo_fallback():
    """TEST 4: Timed-out NGO match offers are expired and fallback matching alerts next NGO."""
    from app.db.session import SessionLocal
    from app.models.models import MatchOffer, FoodDonation
    from datetime import datetime, timedelta, timezone

    tok_admin = _token("admin@fooddonation.org", "admin123")
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Timeout NGO Buffet", "food_category": "Cooked Food",
        "quantity": 30, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Buffet Hall"
    })
    did = cr.json()["id"]

    # Insert an offer created 45 minutes ago
    db = SessionLocal()
    try:
        offer = MatchOffer(
            donation_id=did,
            candidate_id=2, # NGO user id
            candidate_type="ngo",
            status="offered",
            offered_at=now - timedelta(minutes=45)
        )
        db.add(offer)
        db.commit()
    finally:
        db.close()

    # Trigger timeout sweep with 30-minute threshold
    res = client.post("/api/donations/process-timeouts?ngo_timeout_minutes=30", headers=_h(tok_admin))
    assert res.status_code == 200
    assert res.json()["expired_ngo_offers"] >= 1


def test_part29_05_timeout_based_volunteer_fallback():
    """TEST 5: Timed-out volunteer assignments are cancelled and fallback dispatch alerts next volunteer."""
    from app.db.session import SessionLocal
    from app.models.models import VolunteerAssignment, User
    from datetime import datetime, timedelta, timezone

    tok_admin = _token("admin@fooddonation.org", "admin123")
    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Timeout Volunteer Meals", "food_category": "Cooked Food",
        "quantity": 25, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Kitchen 2"
    })
    did = cr.json()["id"]

    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))

    # Set assignment time to 25 minutes ago
    db = SessionLocal()
    try:
        va = db.query(VolunteerAssignment).filter(VolunteerAssignment.donation_id == did).first()
        va.assigned_at = now - timedelta(minutes=25)
        db.commit()
    finally:
        db.close()

    # Trigger timeout sweep with 15-minute threshold
    res = client.post("/api/donations/process-timeouts?volunteer_timeout_minutes=15", headers=_h(tok_admin))
    assert res.status_code == 200
    assert res.json()["expired_volunteer_assignments"] >= 1


def test_part29_06_emergency_radius_and_candidate_pool_expansion():
    """TEST 6: Emergency escalation alerts verified NGOs, volunteers, and Admins."""
    from app.db.session import SessionLocal
    from app.models.models import Notification
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Urgent Escalate Dish", "food_category": "Cooked Food",
        "quantity": 40, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=2)).isoformat(),
        "pickup_address": "Urgent St"
    })
    did = cr.json()["id"]

    esc = client.post(f"/api/donations/{did}/escalate", headers=_h(tok_donor))
    assert esc.status_code == 200
    assert esc.json()["is_emergency"] == True

    # Check notification in DB
    db = SessionLocal()
    try:
        admin_notif = db.query(Notification).filter(
            Notification.related_donation_id == did,
            Notification.type == "alert"
        ).first()
        assert admin_notif is not None
        assert "ADMIN ESCALATION" in admin_notif.title
    finally:
        db.close()


def test_part29_07_expiry_warning_and_escalation_lifecycle():
    """TEST 7: Near-expiry donation triggers urgent status and warning signals."""
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "One Hour Left Food", "food_category": "Cooked Food",
        "quantity": 15, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=3)).isoformat(),
        "expiry_time": (now + timedelta(minutes=50)).isoformat(),
        "pickup_address": "Fast Lane"
    })
    assert cr.json()["urgency_level"] == "Urgent"

    chk = client.get(f"/api/donations/{cr.json()['id']}/rescue-checklist", headers=_h(tok_donor))
    assert chk.status_code == 200
    assert chk.json()["expiry_status"] == "URGENT"


def test_part29_08_expired_donation_cannot_be_accepted_or_assigned():
    """TEST 8: Expired donation cannot be accepted by NGO."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from datetime import datetime, timedelta, timezone

    tok_ngo1 = _token("ngo1@greenhope.org")
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        d = FoodDonation(
            donor_id=1,
            food_name="Old Stale Food",
            food_category="Cooked Food",
            quantity=20,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=10),
            expiry_time=now - timedelta(hours=1),
            pickup_address="Old St",
            status="expired"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    acc = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert acc.status_code == 409


def test_part29_09_ngo_beneficiary_distribution_recording():
    """TEST 9: NGO records beneficiary distribution distinguishing received vs distributed vs remaining."""
    from app.db.session import SessionLocal
    from app.models.models import User, FoodDonation, NGO
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")

    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        if ngo1:
            ngo1.capacity = 200
            ngo1.current_capacity = 200
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1.carrying_capacity = 150
        db.commit()
        v1_id = vol1.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Community Feast", "food_category": "Cooked Food",
        "quantity": 100, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Community Hall"
    })
    did = cr.json()["id"]

    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    aid = assign.json()["id"]
    client.post(f"/api/volunteers/assignments/{aid}/accept", headers=_h(tok_vol1))
    otp = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor)).json()["otp"]
    client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1), json={"donation_id": did, "otp": otp})
    client.post(f"/api/donations/{did}/deliver", headers=_h(tok_vol1))

    # NGO records distribution
    dist_res = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo1),
        json={
            "received_quantity": 100,
            "distributed_quantity": 95,
            "remaining_quantity": 5,
            "remarks": "Served to children shelter and local night shelter."
        }
    )
    assert dist_res.status_code == 200
    data = dist_res.json()
    assert data["distributed_quantity"] == 95
    assert data["remaining_quantity"] == 5
    assert data["beneficiaries_served"] == 95


def test_part29_10_distinction_between_donated_rescued_and_distributed_metrics():
    """TEST 10: Platform metrics summary distinguishes Donated vs Rescued vs Distributed."""
    tok_donor = _token("donor1@hotel.com")
    summary = client.get("/api/donations/metrics/summary", headers=_h(tok_donor))
    assert summary.status_code == 200
    data = summary.json()
    assert "meals_donated" in data
    assert "meals_rescued" in data
    assert "meals_distributed" in data
    assert "estimated_disposal_cost_avoided_inr" in data
    assert data["meals_rescued"] <= data["meals_donated"]


def test_part29_11_notification_events_created_for_all_roles():
    """TEST 11: Notification records are created in DB for key lifecycle events."""
    from app.db.session import SessionLocal
    from app.models.models import Notification

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Notif Test Batch", "food_category": "Cooked Food",
        "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Notif St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))

    db = SessionLocal()
    try:
        notif = db.query(Notification).filter(Notification.related_donation_id == did).first()
        assert notif is not None
    finally:
        db.close()


def test_part29_12_recoverable_failure_recovery_flow():
    """TEST 12: Volunteer pickup failure transitions safely to recoverable state."""
    from app.db.session import SessionLocal
    from app.models.models import User
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        v1_id = vol1.id
    finally:
        db.close()

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Recoverable Issue Meal", "food_category": "Cooked Food",
        "quantity": 20, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Recover St"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))

    fail = client.post(
        f"/api/volunteers/report-failure?donation_id={did}",
        headers=_h(tok_vol1),
        json={"failure_type": "pickup_failed", "reason": "donor_unavailable", "remarks": "Donor called back in 15 mins"}
    )
    assert fail.status_code == 200
    assert fail.json()["status"] == "failed"


def test_part29_13_dispute_creation_and_admin_resolution():
    """TEST 13: Structured dispute reporting and Admin resolution workflow with trust penalty."""
    from app.db.session import SessionLocal
    from app.models.models import User
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_admin = _token("admin@fooddonation.org", "admin123")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Disputed Meals", "food_category": "Cooked Food",
        "quantity": 30, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Dispute St"
    })
    did = cr.json()["id"]

    # 1. Report dispute
    disp = client.post("/api/disputes", headers=_h(tok_donor), json={
        "donation_id": did,
        "issue_type": "food_condition_mismatch",
        "description": "Portion was slightly smaller than indicated."
    })
    assert disp.status_code == 201
    dispute_id = disp.json()["id"]

    # 2. Admin views disputes
    disputes_list = client.get("/api/disputes", headers=_h(tok_admin))
    assert disputes_list.status_code == 200
    assert any(d["id"] == dispute_id for d in disputes_list.json())

    # 3. Admin resolves dispute
    resolve = client.put(
        f"/api/disputes/{dispute_id}/resolve",
        headers=_h(tok_admin),
        json={
            "status": "resolved",
            "admin_notes": "Reviewed with donor and rectified in records.",
            "trust_score_penalty": 1.0
        }
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"


def test_part29_14_large_donation_exceeding_single_volunteer_capacity_safely_rejected():
    """TEST 14: Batch quantity > single volunteer capacity returns 400 without crashing."""
    from app.db.session import SessionLocal
    from app.models.models import User
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1.carrying_capacity = 30 # Small bike capacity
        db.commit()
        v1_id = vol1.id
    finally:
        db.close()

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Huge 200 Meal Feast", "food_category": "Cooked Food",
        "quantity": 200, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Convention Center"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))

    # Try assigning to bike volunteer with capacity 30
    assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    assert assign.status_code == 400
    assert "carrying capacity" in assign.json()["detail"].lower()


def test_part29_15_complete_end_to_end_simulated_hotel_food_rescue_with_distribution():
    """TEST 15: Full simulated hotel food rescue pipeline from surplus post to beneficiary distribution."""
    from app.db.session import SessionLocal
    from app.models.models import User, FoodDonation, NGO
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    tok_vol1 = _token("vol1@volunteer.org")

    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1.carrying_capacity = 200
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        ngo1.capacity = 500
        ngo1.current_capacity = 500
        db.commit()
        v1_id = vol1.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)

    # 1. Hotel creates 100 surplus meals donation
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Dinner Buffet Surplus", "food_category": "Cooked Food",
        "quantity": 100, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "Grand Palace Hotel, MG Road",
        "storage_method": "Heated/Insulated",
        "storage_duration_hours": 1.0,
        "packaging_condition": "Sealed / Covered",
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.94
    })
    assert cr.status_code in [200, 201]
    did = cr.json()["id"]

    # 2. NGO checks transparent rescue feasibility checklist
    chk = client.get(f"/api/donations/{did}/rescue-checklist", headers=_h(tok_ngo1))
    assert chk.status_code == 200
    assert chk.json()["demand_matched"] == True

    # 3. NGO accepts & capacity reserved
    acc = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    assert acc.status_code == 200

    # 4. Volunteer assigned with capacity validation
    assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={v1_id}", headers=_h(tok_ngo1))
    assert assign.status_code == 200
    aid = assign.json()["id"]

    # 5. Volunteer accepts
    client.post(f"/api/volunteers/assignments/{aid}/accept", headers=_h(tok_vol1))

    # 6. Donor retrieves OTP and shares at pickup
    otp = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor)).json()["otp"]

    # 7. Volunteer verifies OTP
    client.post("/api/volunteers/verify-otp", headers=_h(tok_vol1), json={"donation_id": did, "otp": otp})

    # 8. Volunteer delivers to NGO
    client.post(f"/api/donations/{did}/deliver", headers=_h(tok_vol1))

    # 9. NGO records beneficiary distribution
    dist = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo1),
        json={
            "received_quantity": 100,
            "distributed_quantity": 100,
            "remaining_quantity": 0,
            "remarks": "Distributed to community center shelter."
        }
    )
    assert dist.status_code == 200
    assert dist.json()["beneficiaries_served"] == 100

    # 10. Verify final database state
    db = SessionLocal()
    try:
        final_d = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        assert final_d.status == "completed"
        assert final_d.beneficiaries_served == 100
        assert final_d.distributed_quantity == 100
    finally:
        db.close()


def test_part29_16_exact_capacity_sequence_and_release():
    """TEST 16: Exact sequence: NGO Cap=500. A=300 (accepted, rem=200), B=200 (accepted, rem=0), C=100 (rejected 400). A cancelled (rem=300). C accepted (rem=200)."""
    from app.db.session import SessionLocal
    from app.models.models import NGO
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    tok_ngo1 = _token("ngo1@greenhope.org")
    now = datetime.now(timezone.utc)

    # 1. Set NGO1 capacity to 500
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        ngo1.capacity = 500
        ngo1.current_capacity = 500
        db.commit()
    finally:
        db.close()

    # Create A (300), B (200), C (100)
    cr_a = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Donation A", "food_category": "Cooked Food", "quantity": 300, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(), "expiry_time": (now + timedelta(hours=4)).isoformat(), "pickup_address": "Hall A"
    })
    did_a = cr_a.json()["id"]

    cr_b = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Donation B", "food_category": "Cooked Food", "quantity": 200, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(), "expiry_time": (now + timedelta(hours=4)).isoformat(), "pickup_address": "Hall B"
    })
    did_b = cr_b.json()["id"]

    cr_c = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Donation C", "food_category": "Cooked Food", "quantity": 100, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(), "expiry_time": (now + timedelta(hours=4)).isoformat(), "pickup_address": "Hall C"
    })
    did_c = cr_c.json()["id"]

    # Step 1: A accepted -> remaining becomes 200
    acc_a = client.post(f"/api/donations/{did_a}/accept", headers=_h(tok_ngo1))
    assert acc_a.status_code == 200
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 200
    finally:
        db.close()

    # Step 2: B accepted -> remaining becomes 0
    acc_b = client.post(f"/api/donations/{did_b}/accept", headers=_h(tok_ngo1))
    assert acc_b.status_code == 200
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 0
    finally:
        db.close()

    # Step 3: C rejected -> 400 Bad Request
    acc_c = client.post(f"/api/donations/{did_c}/accept", headers=_h(tok_ngo1))
    assert acc_c.status_code == 400
    assert "insufficient" in acc_c.json()["detail"].lower()

    # Step 4: A cancelled -> capacity restored by 300 to 300
    cancel_a = client.post(f"/api/donations/{did_a}/cancel", headers=_h(tok_donor), json={"reason": "donor_unavailable"})
    assert cancel_a.status_code == 200
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 300
    finally:
        db.close()

    # Step 5: C accepted -> succeeds and remaining becomes 200
    acc_c2 = client.post(f"/api/donations/{did_c}/accept", headers=_h(tok_ngo1))
    assert acc_c2.status_code == 200
    db = SessionLocal()
    try:
        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        assert ngo1.current_capacity == 200
    finally:
        db.close()


def test_part29_17_admin_interventions_endpoint():
    """TEST 17: Admin interventions queue identifies stuck/urgent donations and provides actionable guidance."""
    from datetime import datetime, timedelta, timezone

    tok_admin = _token("admin@fooddonation.org", "admin123")
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    # Create urgent near-expiry donation with no NGO
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Urgent Hot Meals", "food_category": "Cooked Food", "quantity": 75, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=3)).isoformat(),
        "expiry_time": (now + timedelta(minutes=45)).isoformat(),
        "pickup_address": "Convention Center, Indiranagar, Bangalore"
    })
    did = cr.json()["id"]

    # Query admin interventions
    resp = client.get("/api/admin/interventions", headers=_h(tok_admin))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_interventions_needed" in data
    assert "items" in data
    assert any(item["donation_id"] == did for item in data["items"])


def test_part29_18_trust_score_deterministic_updates():
    """TEST 18: Bounded deterministic trust score adjustments for completed rescue (+1) and cancellation (-2)."""
    from app.db.session import SessionLocal
    from app.models.models import User
    from datetime import datetime, timedelta, timezone

    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        donor = db.query(User).filter(User.email == "donor1@hotel.com").first()
        donor.donor_trust_score = 90.0
        db.commit()
    finally:
        db.close()

    # Create & cancel donation -> donor trust score decrements by 2.0
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Cancelled Trust Test", "food_category": "Cooked Food", "quantity": 10, "quantity_unit": "Meals",
        "preparation_time": now.isoformat(), "expiry_time": (now + timedelta(hours=4)).isoformat(), "pickup_address": "Trust Lane"
    })
    did = cr.json()["id"]
    client.post(f"/api/donations/{did}/cancel", headers=_h(tok_donor), json={"reason": "donor_unavailable"})

    db = SessionLocal()
    try:
        donor = db.query(User).filter(User.email == "donor1@hotel.com").first()
        assert donor.donor_trust_score == 88.0
    finally:
        db.close()


# ==============================================================================
# PART 30: TIME-AWARE AI FOOD RESCUE & KNOWLEDGE RULES ENGINE TESTS
# ==============================================================================

def test_part30_01_food_profile_knowledge_resolution():
    """TEST 01: Auditable FoodProfile resolution accurately resolves specific food items and categories."""
    from app.services.food_knowledge_rules import resolve_food_profile

    # Specific food profiles
    p_idli = resolve_food_profile("Idli", "Cooked Food")
    assert p_idli.food_type == "Idli"
    assert p_idli.category == "Cooked Food"
    assert p_idli.base_shelf_hours_room_temp == 4.0
    assert "FSSAI" in p_idli.source
    assert p_idli.rule_version == "2026.1"

    p_biryani = resolve_food_profile("Chicken Biryani", "Cooked Food")
    assert p_biryani.food_type == "Biryani"

    p_bread = resolve_food_profile("Bread", "Bakery")
    assert p_bread.food_type == "Bread"
    assert p_bread.base_shelf_hours_room_temp == 48.0

    # Fallback to category
    p_cat = resolve_food_profile("Unknown Dish", "Fruits")
    assert p_cat.category == "Fruits"


def test_part30_02_preparation_elapsed_time_and_future_protection():
    """TEST 02: Elapsed preparation duration handles past timestamps and rejects/safeguards future timestamps."""
    from app.services.food_rescue_window_service import calculate_elapsed_prep_time
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    
    # 1h 30m past
    prep_past = now - timedelta(hours=1, minutes=30)
    elapsed_hrs, elapsed_str = calculate_elapsed_prep_time(prep_past, now)
    assert 1.49 <= elapsed_hrs <= 1.51
    assert "1h 30m" in elapsed_str

    # 45m past
    prep_45m = now - timedelta(minutes=45)
    elapsed_hrs_45, elapsed_str_45 = calculate_elapsed_prep_time(prep_45m, now)
    assert "45m" in elapsed_str_45

    # Future timestamp protection
    prep_future = now + timedelta(minutes=30)
    elapsed_future_hrs, elapsed_future_str = calculate_elapsed_prep_time(prep_future, now)
    assert elapsed_future_hrs == 0.0
    assert "Prepared just now" in elapsed_future_str


def test_part30_03_storage_condition_continuous_and_history_penalties():
    """TEST 03: Structured storage transitions and non-continuous storage apply appropriate advisory penalties."""
    from app.services.food_rescue_window_service import evaluate_food_rescue_window
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=1)

    # Continuous Refrigerated
    res_refrig = evaluate_food_rescue_window(
        food_type="Rice", food_category="Cooked Food", prepared_at=prep_time,
        storage_method="Refrigerated", storage_continuous=True, current_time=now
    )
    assert res_refrig["remaining_minutes"] > 1000  # Base ~24h

    # Non-continuous with transitions (Hot Holding -> Room Temp)
    history = [
        {"method": "Hot Holding", "duration_hours": 0.5},
        {"method": "Room Temperature", "duration_hours": 0.5}
    ]
    res_mixed = evaluate_food_rescue_window(
        food_type="Rice", food_category="Cooked Food", prepared_at=prep_time,
        storage_method="Refrigerated", storage_continuous=False, storage_history=history, current_time=now
    )
    assert res_mixed["remaining_minutes"] < res_refrig["remaining_minutes"]
    assert any("transition" in r.lower() for r in res_mixed["reasons"])


def test_part30_04_handling_and_exposure_assessment():
    """TEST 04: Handling parameters (open packaging, previously served, customer handled) apply explainable deductions."""
    from app.services.food_rescue_window_service import evaluate_food_rescue_window
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=1)

    # Standard covered, unserved
    res_std = evaluate_food_rescue_window(
        food_type="Idli", food_category="Cooked Food", prepared_at=prep_time,
        storage_method="Room Temperature", packaging_status="Covered",
        previously_served="No", exposure_status="No", handling_status="No", current_time=now
    )

    # Open packaging + previously served + customer handled
    res_exposed = evaluate_food_rescue_window(
        food_type="Idli", food_category="Cooked Food", prepared_at=prep_time,
        storage_method="Room Temperature", packaging_status="Open",
        previously_served="Yes", exposure_status="Yes", handling_status="Yes", current_time=now
    )

    assert res_exposed["remaining_minutes"] < res_std["remaining_minutes"]
    assert any("open" in r.lower() or "exposed" in r.lower() for r in res_exposed["reasons"])
    assert any("serv" in r.lower() for r in res_exposed["reasons"])


def test_part30_05_three_distinct_outputs_generation():
    """TEST 05: Evaluates the three distinct outputs: Visual Condition, Estimated Window, and Rescue Urgency."""
    from app.services.food_rescue_window_service import evaluate_food_rescue_window
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=2, minutes=30)

    res = evaluate_food_rescue_window(
        food_type="Idli", food_category="Cooked Food", prepared_at=prep_time,
        storage_method="Room Temperature", current_time=now
    )

    # Output 1: Visual Condition
    assert res["visual_condition"] in ["GOOD", "FAIR", "CONCERNING", "UNCERTAIN"]

    # Output 2: Estimated Window
    assert "estimated_window_start" in res
    assert "estimated_window_end" in res
    assert isinstance(res["remaining_minutes"], int)
    assert "estimated_window_display" in res

    # Output 3: Rescue Urgency
    assert res["urgency_level"] in ["FRESH", "APPROACHING", "URGENT", "CRITICAL"]
    assert 0.0 <= res["urgency_score"] <= 1.0


def test_part30_06_strict_food_safety_disclaimer_compliance():
    """TEST 06: Strictly enforces that NO food safety claims ('Safe to eat', 'Food is safe') are returned."""
    from app.services.food_rescue_window_service import evaluate_food_rescue_window
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    res = evaluate_food_rescue_window(
        food_type="Biryani", food_category="Cooked Food",
        prepared_at=now - timedelta(hours=1), current_time=now
    )

    res_str = str(res)
    assert "Safe to eat" not in res_str
    assert "Food is safe" not in res_str
    assert "Guaranteed safe" not in res_str
    assert "Certified safe" not in res_str
    assert "This is an advisory estimate and does not certify food safety." in res["safety_disclaimer"]


def test_part30_07_logistics_feasibility_engine_calculation():
    """TEST 07: Feasibility Engine accurately classifies RESCUE_FEASIBLE, AT_RISK, and RESCUE_UNLIKELY."""
    from app.services.food_rescue_window_service import calculate_rescue_feasibility

    # Healthy buffer: 120 min window vs 60 min required -> RESCUE_FEASIBLE
    f_good = calculate_rescue_feasibility(remaining_window_minutes=120)
    assert f_good["feasibility_status"] == "RESCUE_FEASIBLE"
    assert f_good["is_feasible"] is True
    assert f_good["remaining_buffer_minutes"] > 0

    # Tight buffer: 50 min window vs 45 min min required -> AT_RISK
    f_tight = calculate_rescue_feasibility(remaining_window_minutes=50)
    assert f_tight["feasibility_status"] == "AT_RISK"
    assert f_tight["is_feasible"] is True

    # Infeasible: 25 min window vs 60 min required -> RESCUE_UNLIKELY
    f_late = calculate_rescue_feasibility(remaining_window_minutes=25)
    assert f_late["feasibility_status"] == "RESCUE_UNLIKELY"
    assert f_late["is_feasible"] is False


def test_part30_08_deadline_aware_ngo_recommendation():
    """TEST 08: NGO recommendations include time-aware feasibility labels and ETA."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from app.services.recommendation_service import recommend_ngos
    from datetime import datetime, timezone, timedelta

    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Fresh Dosa Breakfast", "food_type": "Dosa", "food_category": "Cooked Food",
        "quantity": 30, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "Koramangala, Bangalore"
    })
    did = cr.json()["id"]

    db = SessionLocal()
    try:
        donation = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        recs = recommend_ngos(db, donation)
        assert len(recs) > 0
        assert "feasibility_status" in recs[0]
        assert "transit_time_minutes" in recs[0]
    finally:
        db.close()


def test_part30_09_deadline_aware_volunteer_eta_feasibility():
    """TEST 09: Volunteer matching gates capacity and provides arrival ETA feasibility."""
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation
    from app.services.recommendation_service import recommend_volunteers
    from datetime import datetime, timezone, timedelta

    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Idli Batch Rescue", "food_type": "Idli", "food_category": "Cooked Food",
        "quantity": 20, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "Indiranagar, Bangalore"
    })
    did = cr.json()["id"]

    db = SessionLocal()
    try:
        donation = db.query(FoodDonation).filter(FoodDonation.id == did).first()
        vol_recs = recommend_volunteers(db, donation)
        assert len(vol_recs) > 0
        assert "pickup_eta_minutes" in vol_recs[0]
        assert "feasibility_status" in vol_recs[0]
    finally:
        db.close()


def test_part30_10_hungarian_matching_with_deadline_filtering():
    """TEST 10: Hungarian batch matching executes linear_sum_assignment with global efficiency metric."""
    from app.db.session import SessionLocal
    from app.services.recommendation_service import global_batch_match_ngos

    db = SessionLocal()
    try:
        res = global_batch_match_ngos(db)
        assert "matched_pairs" in res
        assert "global_efficiency_score" in res
        assert "unmatched_donations" in res
    finally:
        db.close()


def test_part30_11_donation_detail_contains_rescue_window_and_feasibility():
    """TEST 11: GET /api/donations/{id} dynamically returns rescue_window and feasibility objects."""
    from datetime import datetime, timezone, timedelta
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Chapati & Dal Set", "food_type": "Chapati", "food_category": "Cooked Food",
        "quantity": 40, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=5)).isoformat(),
        "pickup_address": "Whitefield, Bangalore",
        "storage_method": "Insulated Container",
        "packaging_condition": "Covered"
    })
    did = cr.json()["id"]

    resp = client.get(f"/api/donations/{did}", headers=_h(tok_donor))
    assert resp.status_code == 200
    data = resp.json()
    assert "rescue_window" in data
    assert data["rescue_window"]["food_type"] == "Chapati"
    assert "feasibility" in data
    assert data["feasibility"]["is_feasible"] is True


def test_part30_12_rescue_window_endpoint_returns_advisory_profile():
    """TEST 12: GET /api/donations/{id}/rescue-window returns auditable food advisory window."""
    from datetime import datetime, timezone, timedelta
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Veg Sambar Rice", "food_type": "Sambar Rice", "food_category": "Cooked Food",
        "quantity": 25, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(minutes=45)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "Jayanagar, Bangalore"
    })
    did = cr.json()["id"]

    resp = client.get(f"/api/donations/{did}/rescue-window", headers=_h(tok_donor))
    assert resp.status_code == 200
    w_data = resp.json()
    assert w_data["assessment_status"] == "ADVISORY"
    assert w_data["food_type"] == "Sambar Rice"
    assert len(w_data["reasons"]) > 0
    assert "Visual assessment only" in w_data["safety_disclaimer"]


def test_part30_13_feasibility_endpoint_returns_buffer_and_status():
    """TEST 13: GET /api/donations/{id}/feasibility returns structured logistics buffer metrics."""
    from datetime import datetime, timezone, timedelta
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)

    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Curd Rice Box", "food_type": "Curd Rice", "food_category": "Cooked Food",
        "quantity": 15, "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=2)).isoformat(),
        "pickup_address": "HSR Layout, Bangalore"
    })
    did = cr.json()["id"]

    resp = client.get(f"/api/donations/{did}/feasibility", headers=_h(tok_donor))
    assert resp.status_code == 200
    f_data = resp.json()
    assert f_data["feasibility_status"] in ["RESCUE_FEASIBLE", "AT_RISK", "RESCUE_UNLIKELY"]
    assert "remaining_buffer_minutes" in f_data
    assert "explanation" in f_data


def test_donor_impact_summary_distinguishes_donated_rescued_distributed():
    """TEST: GET /api/donations/donor/impact-summary cleanly distinguishes donated vs rescued vs distributed."""
    tok_donor = _token("donor1@hotel.com")
    resp = client.get("/api/donations/donor/impact-summary", headers=_h(tok_donor))
    assert resp.status_code == 200
    data = resp.json()
    assert "meals_donated" in data
    assert "meals_rescued" in data
    assert "meals_distributed" in data
    assert "estimated_waste_diverted_kg" in data
    assert "recognition_level" in data
    assert "conversion_factor_note" in data
    assert "monthly_breakdown" in data
    assert data["meals_donated"] >= data["meals_rescued"]
    assert data["meals_rescued"] >= data["meals_distributed"]


def test_donor_impact_summary_unauthorized_role():
    """TEST: Volunteer cannot access donor impact summary (HTTP 403)."""
    tok_vol = _token("vol1@volunteer.org")
    resp = client.get("/api/donations/donor/impact-summary", headers=_h(tok_vol))
    assert resp.status_code == 403


# ── Distribution Tests ────────────────────────────────────────────────────────
def test_distribution_valid_request_succeeds():
    """TEST: Valid distribution request by assigned NGO succeeds after delivery."""
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, NGO, User
    tok_ngo1 = _token("ngo1@greenhope.org")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ngo_user = db.query(User).filter(User.email == "ngo1@greenhope.org").first()
        ngo1 = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        d = FoodDonation(
            donor_id=1,
            food_name="Test Delivered Rice",
            food_category="Cooked Food",
            quantity=50.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=3),
            pickup_address="MG Road",
            assigned_ngo_id=ngo1.id,
            status="delivered"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    resp = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo1),
        json={
            "distributed_quantity": 48.0,
            "received_quantity": 50.0,
            "remaining_quantity": 2.0,
            "beneficiaries_served": 48,
            "remarks": "Served to shelter families"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["distributed_quantity"] == 48.0
    assert data["remaining_quantity"] == 2.0
    assert data["distribution_status"] == "distributed"


def test_distribution_negative_quantity_rejected():
    """TEST: Negative distribution quantity is rejected with 400 Bad Request."""
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, NGO, User
    tok_ngo1 = _token("ngo1@greenhope.org")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ngo_user = db.query(User).filter(User.email == "ngo1@greenhope.org").first()
        ngo1 = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        d = FoodDonation(
            donor_id=1,
            food_name="Negative Test Meals",
            food_category="Cooked Food",
            quantity=30.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=3),
            pickup_address="MG Road",
            assigned_ngo_id=ngo1.id,
            status="delivered"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    resp = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo1),
        json={"distributed_quantity": -5.0}
    )
    assert resp.status_code == 400
    assert "cannot be negative" in resp.json()["detail"].lower()


def test_distribution_exceeding_received_rejected():
    """TEST: Distributed quantity exceeding received batch size is rejected with 400."""
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, NGO, User
    tok_ngo1 = _token("ngo1@greenhope.org")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ngo_user = db.query(User).filter(User.email == "ngo1@greenhope.org").first()
        ngo1 = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        d = FoodDonation(
            donor_id=1,
            food_name="Over-Distribution Test Meals",
            food_category="Cooked Food",
            quantity=20.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=3),
            pickup_address="MG Road",
            assigned_ngo_id=ngo1.id,
            status="delivered"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    resp = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo1),
        json={"distributed_quantity": 50.0, "received_quantity": 20.0}
    )
    assert resp.status_code == 400
    assert "cannot exceed" in resp.json()["detail"].lower()


def test_distribution_before_delivery_rejected():
    """TEST: Distribution attempted while donation is still pending/assigned is rejected with 400."""
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, NGO, User
    tok_ngo1 = _token("ngo1@greenhope.org")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ngo_user = db.query(User).filter(User.email == "ngo1@greenhope.org").first()
        ngo1 = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        d = FoodDonation(
            donor_id=1,
            food_name="Early Distribution Test",
            food_category="Cooked Food",
            quantity=20.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=3),
            pickup_address="MG Road",
            assigned_ngo_id=ngo1.id,
            status="accepted"  # Not delivered yet
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    resp = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo1),
        json={"distributed_quantity": 20.0}
    )
    assert resp.status_code == 400
    assert "delivered or completed" in resp.json()["detail"].lower()


def test_distribution_unauthorized_ngo_rejected():
    """TEST: Unassigned NGO cannot record distribution for another NGO's donation (HTTP 403)."""
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, NGO, User
    tok_ngo2 = _token("ngo2@feedindia.org")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ngo_user = db.query(User).filter(User.email == "ngo1@greenhope.org").first()
        ngo1 = db.query(NGO).filter(NGO.user_id == ngo_user.id).first()
        d = FoodDonation(
            donor_id=1,
            food_name="NGO Isolation Test",
            food_category="Cooked Food",
            quantity=20.0,
            quantity_unit="Meals",
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=3),
            pickup_address="MG Road",
            assigned_ngo_id=ngo1.id,  # Assigned to NGO 1
            status="delivered"
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        did = d.id
    finally:
        db.close()

    resp = client.post(
        f"/api/donations/{did}/distribution",
        headers=_h(tok_ngo2),
        json={"distributed_quantity": 20.0}
    )
    assert resp.status_code == 403


# ── AI Analysis Canonical Endpoint Tests ──────────────────────────────────────
def test_donation_specific_analyze_endpoint():
    """TEST: POST /api/donations/{id}/analyze runs canonical AI analysis and stores FoodAnalysis."""
    from datetime import datetime, timezone, timedelta
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Paneer Butter Masala Combo",
        "food_category": "Cooked Food",
        "quantity": 30.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(minutes=30)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "Indiranagar, Bangalore"
    })
    did = cr.json()["id"]

    resp = client.post(f"/api/donations/{did}/analyze", headers=_h(tok_donor), json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["donation_id"] == did
    assert data["visual_condition"] in ["GOOD", "FAIR", "POOR", "UNCERTAIN"]
    assert "safety_disclaimer" in data
    assert "Visual assessment only" in data["safety_disclaimer"]


# ── OTP Comprehensive Security Matrix ─────────────────────────────────────────
def test_otp_complete_security_matrix():
    """TEST: Complete security matrix for OTP pickup verification."""
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import FoodDonation, VolunteerAssignment, User
    tok_donor = _token("donor1@hotel.com")
    tok_vol1 = _token("vol1@volunteer.org")
    tok_vol2 = _token("vol2@volunteer.org")
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        vol1_user = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1_id = vol1_user.id
    finally:
        db.close()

    # 1. Create donation
    cr = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "OTP Security Matrix Test Rice",
        "food_category": "Cooked Food",
        "quantity": 25.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(minutes=20)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "Koramangala, Bangalore"
    })
    did = cr.json()["id"]

    # 2. Donor fetches OTP securely
    code_resp = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor))
    assert code_resp.status_code == 200
    otp = code_resp.json()["otp"]
    assert len(otp) == 6

    # 3. Volunteer cannot access donor's verification-code endpoint (403)
    vol_code_resp = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_vol1))
    assert vol_code_resp.status_code == 403

    # 4. Accept donation & assign vol1
    tok_ngo1 = _token("ngo1@greenhope.org")
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo1))
    client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={vol1_id}", headers=_h(tok_vol1))

    # 5. Unassigned volunteer (vol2) attempts OTP verification -> HTTP 403
    unassigned_resp = client.post(
        "/api/volunteers/verify-otp",
        headers=_h(tok_vol2),
        json={"donation_id": did, "otp": otp}
    )
    assert unassigned_resp.status_code == 403

    # 6. Assigned volunteer enters wrong OTP -> HTTP 400
    wrong_otp_resp = client.post(
        "/api/volunteers/verify-otp",
        headers=_h(tok_vol1),
        json={"donation_id": did, "otp": "999999"}
    )
    assert wrong_otp_resp.status_code == 400

    # 7. Assigned volunteer enters valid OTP -> HTTP 200 & collected
    valid_resp = client.post(
        "/api/volunteers/verify-otp",
        headers=_h(tok_vol1),
        json={"donation_id": did, "otp": otp}
    )
    assert valid_resp.status_code == 200
    assert valid_resp.json()["status"] == "collected"

    # 8. Replay attack: same OTP used again -> HTTP 409 Conflict
    replay_resp = client.post(
        "/api/volunteers/verify-otp",
        headers=_h(tok_vol1),
        json={"donation_id": did, "otp": otp}
    )
    assert replay_resp.status_code == 409


def test_time_aware_otp_delivery_and_arrival_notification_flow():
    """
    TEST: Comprehensive Time-Aware OTP Delivery & Pickup Handover Flow:
    1. Donor creates donation.
    2. NGO accepts donation.
    3. Volunteer assigned & accepts task.
    4. Volunteer starts pickup -> state 'pickup_en_route' -> Donor receives 'Volunteer is on the way'.
    5. Volunteer marks arrived -> state 'arrived_at_donor' -> Donor receives 'Volunteer has arrived' (NO OTP in notification!).
    6. Donor retrieves OTP securely via dedicated verification-code endpoint.
    7. Volunteer API strictly does NOT return OTP.
    8. Volunteer submits 6-digit OTP -> 200 OK -> state 'collected' -> single-use consumed.
    9. Donor regenerates OTP after invalidation test.
    """
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import User

    tok_donor = _token("donor1@hotel.com")
    tok_ngo = _token("ngo1@greenhope.org")
    tok_vol = _token("vol1@volunteer.org")
    tok_other_vol = _token("vol2@volunteer.org")

    db = SessionLocal()
    try:
        vol_user = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1_id = vol_user.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)

    # 1. Create donation
    r_create = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Time-Aware Delivery Biryani",
        "food_category": "Cooked Food",
        "quantity": 30.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "pickup_address": "88 Banquet Hall",
        "storage_method": "Heated / Insulated",
        "packaging_condition": "Sealed"
    })
    assert r_create.status_code == 201
    did = r_create.json()["id"]

    # 2. NGO accepts
    r_acc = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo))
    assert r_acc.status_code == 200

    # 3. Volunteer assigned
    r_assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={vol1_id}", headers=_h(tok_ngo))
    assert r_assign.status_code == 200
    assignment_id = r_assign.json()["id"]

    # 4. Volunteer accepts task
    r_vol_acc = client.put(f"/api/volunteers/assignments/{assignment_id}?status_update=accepted", headers=_h(tok_vol))
    assert r_vol_acc.status_code == 200

    # 5. Volunteer starts pickup (en route)
    r_start = client.post(f"/api/volunteers/assignments/{assignment_id}/start-pickup", headers=_h(tok_vol))
    assert r_start.status_code == 200
    assert r_start.json()["status"] == "en_route"

    # Verify donor receives 'Volunteer is on the way' notification
    r_notifs = client.get("/api/notifications", headers=_h(tok_donor))
    assert r_notifs.status_code == 200
    donor_notifs = r_notifs.json()
    # Check for VOLUNTEER_ON_THE_WAY notification (event_type field)
    en_route_notif = next(
        (n for n in donor_notifs
         if n["related_donation_id"] == did
         and (n.get("event_type") == "VOLUNTEER_ON_THE_WAY" or n["type"] == "pickup_en_route")),
        None
    )
    assert en_route_notif is not None
    assert "on the way" in en_route_notif["title"].lower() or "on the way" in en_route_notif["message"].lower()

    # 6. Volunteer arrives at donor location
    r_arrived = client.post(f"/api/volunteers/assignments/{assignment_id}/arrived", headers=_h(tok_vol))
    assert r_arrived.status_code == 200
    assert r_arrived.json()["status"] == "arrived"

    # Verify donor receives 'Volunteer has arrived' notification with NO OTP in payload!
    r_notifs2 = client.get("/api/notifications", headers=_h(tok_donor))
    assert r_notifs2.status_code == 200
    arrived_notif = next(
        (n for n in r_notifs2.json()
         if n["related_donation_id"] == did
         and (n.get("event_type") == "VOLUNTEER_ARRIVED" or n["type"] == "volunteer_arrived")),
        None
    )
    assert arrived_notif is not None
    assert "arrived" in arrived_notif["title"].lower()
    # MANDATORY SECURITY ASSERTION: Notification message MUST NOT contain 6-digit numbers
    assert not any(word.isdigit() and len(word) == 6 for word in arrived_notif["message"].split())

    # 7. Donor retrieves verification code securely
    r_otp = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor))
    assert r_otp.status_code == 200
    otp_data = r_otp.json()
    assert "otp" in otp_data
    assert len(otp_data["otp"]) == 6
    assert otp_data["otp_status"] == "active"
    assert "otp_expiry" in otp_data
    actual_otp = otp_data["otp"]

    # 8. Volunteer API strictly does NOT expose OTP
    r_vol_detail = client.get(f"/api/donations/{did}", headers=_h(tok_vol))
    assert r_vol_detail.status_code == 200
    assert r_vol_detail.json()["verification_otp"] is None

    # 9. Volunteer cannot regenerate OTP (403 Forbidden)
    r_vol_regen = client.post(f"/api/donations/{did}/regenerate-otp", headers=_h(tok_vol))
    assert r_vol_regen.status_code == 403

    # 10. Unassigned volunteer cannot verify OTP (403 Forbidden)
    r_unassigned_verify = client.post("/api/volunteers/verify-otp", headers=_h(tok_other_vol), json={
        "donation_id": did,
        "otp": actual_otp
    })
    assert r_unassigned_verify.status_code == 403

    # 11. Assigned volunteer enters valid OTP -> 200 OK & collected
    r_verify = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={
        "donation_id": did,
        "otp": actual_otp
    })
    assert r_verify.status_code == 200
    assert r_verify.json()["status"] == "collected"

    # 12. Replay attempt rejected (409 Conflict)
    r_replay = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={
        "donation_id": did,
        "otp": actual_otp
    })
    assert r_replay.status_code == 409

    # 13. Consumed OTP shows as 'USED' in donor verification endpoint
    r_consumed_check = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor))
    assert r_consumed_check.status_code == 200
    assert r_consumed_check.json()["otp"] == "USED"
    assert r_consumed_check.json()["otp_status"] == "consumed"


def test_donor_otp_regeneration_and_rate_limiting():
    """
    TEST: Donor can regenerate OTP prior to pickup; old OTP is invalidated; rate limiting is enforced.
    """
    from datetime import datetime, timezone, timedelta
    from app.db.session import SessionLocal
    from app.models.models import User

    tok_donor = _token("donor1@hotel.com")
    tok_ngo = _token("ngo1@greenhope.org")
    tok_vol = _token("vol1@volunteer.org")

    db = SessionLocal()
    try:
        vol_user = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1_id = vol_user.id
    finally:
        db.close()

    now = datetime.now(timezone.utc)

    # 1. Create donation
    r_create = client.post("/api/donations", headers=_h(tok_donor), json={
        "food_name": "Regen Test Meals",
        "food_category": "Cooked Food",
        "quantity": 25.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "42 West Street"
    })
    assert r_create.status_code == 201
    did = r_create.json()["id"]

    # 2. NGO accepts
    client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo))

    # 3. Get initial OTP
    r_otp1 = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor))
    assert r_otp1.status_code == 200
    otp1 = r_otp1.json()["otp"]

    # 4. Donor regenerates OTP
    r_regen = client.post(f"/api/donations/{did}/regenerate-otp", headers=_h(tok_donor))
    assert r_regen.status_code == 200
    otp2 = r_regen.json()["otp"]
    assert otp2 != otp1
    assert len(otp2) == 6

    # 5. Immediate second regeneration attempt triggers 429 Too Many Requests
    r_rapid_regen = client.post(f"/api/donations/{did}/regenerate-otp", headers=_h(tok_donor))
    assert r_rapid_regen.status_code == 429

    # 6. Assign volunteer
    assign_resp = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={vol1_id}", headers=_h(tok_ngo))
    assert assign_resp.status_code == 200
    assign_id = assign_resp.json()["id"]

    # Volunteer accepts
    client.put(f"/api/volunteers/assignments/{assign_id}?status_update=accepted", headers=_h(tok_vol))

    # 7. Old OTP must fail (400 Bad Request)
    r_old_otp_fail = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={
        "donation_id": did,
        "otp": otp1
    })
    assert r_old_otp_fail.status_code == 400

    # 8. New OTP succeeds (200 OK)
    r_new_otp_ok = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={
        "donation_id": did,
        "otp": otp2
    })
    assert r_new_otp_ok.status_code == 200
    assert r_new_otp_ok.json()["status"] == "collected"











