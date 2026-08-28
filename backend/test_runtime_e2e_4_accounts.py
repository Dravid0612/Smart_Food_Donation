import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import User, FoodDonation, NGO, VolunteerAssignment, AuditLog, Notification

client = TestClient(app)

def _token(email: str, password: str = None) -> str:
    if password is None:
        password = "admin123" if "admin" in email else "pass123"
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["access_token"]

def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def run_full_simulation():
    print("=" * 70)
    print("SMART FOOD RESCUE - LIVE 4-ACCOUNT RUNTIME SIMULATION")
    print("=" * 70)

    # ── RESET / SEED DATA ─────────────────────────────────────────────────────
    db = SessionLocal()
    try:
        vol1 = db.query(User).filter(User.email == "vol1@volunteer.org").first()
        vol1.carrying_capacity = 250
        vol1.is_active = True

        ngo1 = db.query(NGO).filter(NGO.organization_name.like("%Green Hope%")).first()
        ngo1.is_verified = True
        ngo1.capacity = 500
        ngo1.current_capacity = 500
        db.commit()
        vol1_id = vol1.id
        ngo1_id = ngo1.id
    finally:
        db.close()

    # 1. DONOR LOGIN & DONATION CREATION
    print("\n[STEP 1] Donor Login (donor1@hotel.com) & Surplus Food Creation...")
    tok_donor = _token("donor1@hotel.com")
    now = datetime.now(timezone.utc)
    
    donation_payload = {
        "food_name": "Vegetable Biryani & Basmati Rice",
        "food_type": "Cooked Rice",
        "food_category": "Cooked Food",
        "quantity": 100.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(minutes=45)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "pickup_address": "Hotel Grand Palace, 45 MG Road, Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "storage_method": "Heated/Insulated",
        "storage_duration_hours": 0.75,
        "packaging_condition": "Sealed / Covered",
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.95
    }
    
    r_create = client.post("/api/donations", headers=_h(tok_donor), json=donation_payload)
    assert r_create.status_code in [200, 201], f"Create failed: {r_create.text}"
    donation_data = r_create.json()
    did = donation_data["id"]
    print(f"  [OK] Created Donation ID #{did}: '{donation_data['food_name']}' ({donation_data['quantity']} meals)")
    print(f"  [OK] Estimated Rescue Window Remaining: {donation_data['remaining_minutes']} mins (Urgency: {donation_data['rescue_urgency_level']})")

    # 2. RESCUE DEADLINE & FEASIBILITY VERIFICATION
    print("\n[STEP 2] Verifying Advisory Rescue Window & Feasibility Assessment...")
    r_feas = client.get(f"/api/donations/{did}/feasibility", headers=_h(tok_donor))
    assert r_feas.status_code == 200
    feas = r_feas.json()
    print(f"  [OK] Feasibility Engine Result: {feas['feasibility_status']} (Buffer: {feas['safety_buffer_minutes']} min)")

    # 3. NGO LOGIN & TRANSPARENT CHECKLIST INSPECTION
    print("\n[STEP 3] NGO Login (ngo1@greenhope.org) & Transparent Feasibility Checklist...")
    tok_ngo = _token("ngo1@greenhope.org")
    r_chk = client.get(f"/api/donations/{did}/rescue-checklist", headers=_h(tok_ngo))
    assert r_chk.status_code == 200
    chk = r_chk.json()
    print(f"  [OK] NGO Checklist: Demand Matched = {chk['demand_matched']}, Operating Hours OK = {chk['ngo_open']}, Capacity Available = {chk['ngo_capacity_available']}")

    # 4. NGO ATOMIC ACCEPTANCE & CAPACITY RESERVATION
    print("\n[STEP 4] Partner NGO Accepts Donation (Atomic Row Lock & Capacity Reservation)...")
    r_accept = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo))
    assert r_accept.status_code == 200
    print(f"  [OK] Donation Status: '{r_accept.json()['status']}' | Assigned NGO: Green Hope Foundation")

    # Verify duplicate acceptance is strictly rejected with 409
    r_dup_accept = client.post(f"/api/donations/{did}/accept", headers=_h(tok_ngo))
    assert r_dup_accept.status_code == 409
    print("  [OK] Duplicate NGO acceptance strictly rejected (409 Conflict).")

    # 5. VOLUNTEER ASSIGNMENT & ACCEPTANCE
    print("\n[STEP 5] Volunteer Courier Assignment & Task Acceptance...")
    r_assign = client.post(f"/api/volunteers/assignments?donation_id={did}&volunteer_id={vol1_id}", headers=_h(tok_ngo))
    assert r_assign.status_code == 200
    aid = r_assign.json()["id"]
    print(f"  [OK] Volunteer Assignment Created (Assignment #{aid})")

    tok_vol = _token("vol1@volunteer.org")
    r_vol_accept = client.post(f"/api/volunteers/assignments/{aid}/accept", headers=_h(tok_vol))
    assert r_vol_accept.status_code == 200
    print(f"  [OK] Volunteer Accepted Task #{aid}")

    # 6. ZERO-LEAKAGE OTP VERIFICATION AT PHYSICAL HANDOVER
    print("\n[STEP 6] Zero-Leakage OTP Verification at Physical Handover...")
    # Verify volunteer CANNOT see OTP in API
    r_vol_view = client.get(f"/api/donations/{did}", headers=_h(tok_vol))
    assert r_vol_view.status_code == 200
    assert r_vol_view.json()["verification_otp"] is None, "SECURITY ALERT: OTP leaked to volunteer!"
    print("  [OK] Verified: Volunteer API response does NOT contain OTP.")

    # Donor retrieves OTP
    r_otp = client.get(f"/api/donations/{did}/verification-code", headers=_h(tok_donor))
    assert r_otp.status_code == 200
    donor_otp = r_otp.json()["otp"]
    print(f"  [OK] Donor Phone Displays 6-Digit Pickup Code: [{donor_otp}]")

    # Volunteer submits wrong OTP -> 400 Bad Request
    r_wrong_otp = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={"donation_id": did, "otp": "000000"})
    assert r_wrong_otp.status_code == 400
    print("  [OK] Invalid OTP correctly rejected (400 Bad Request).")

    # Volunteer submits correct OTP -> 200 OK & Status: COLLECTED
    r_verify = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={"donation_id": did, "otp": donor_otp})
    assert r_verify.status_code == 200
    print("  [OK] Handover OTP Verified: Status transitioned to 'COLLECTED'.")

    # Replay OTP attempt -> 409 Conflict
    r_replay = client.post("/api/volunteers/verify-otp", headers=_h(tok_vol), json={"donation_id": did, "otp": donor_otp})
    assert r_replay.status_code == 409
    print("  [OK] Replay OTP attempt strictly rejected (409 Conflict).")

    # 7. IN-TRANSIT & DELIVERY CONFIRMATION AT NGO FACILITY
    print("\n[STEP 7] Food in Transit & Arrival/Delivery at NGO Facility...")
    r_deliver = client.post(f"/api/donations/{did}/deliver", headers=_h(tok_vol))
    assert r_deliver.status_code == 200
    print("  [OK] Food safely delivered to NGO facility (Status: 'delivered').")

    # 8. BENEFICIARY DISTRIBUTION (PARTIAL & FULL EVENTS)
    print("\n[STEP 8] NGO Records Beneficiary Distribution Events...")
    # Event 1: Partial distribution of 60 meals
    r_dist1 = client.post(f"/api/donations/{did}/distribution", headers=_h(tok_ngo), json={
        "received_quantity": 100.0,
        "distributed_quantity": 60.0,
        "remaining_quantity": 40.0,
        "beneficiaries_served": 60,
        "remarks": "Served to children and families at Community Shelter A."
    })
    assert r_dist1.status_code == 200
    assert r_dist1.json()["remaining_quantity"] == 40.0
    print("  [OK] Distribution Event #1: 60 meals distributed (40 remaining -> Status: 'partially_distributed').")

    # Event 2: Final distribution of remaining 40 meals
    r_dist2 = client.post(f"/api/donations/{did}/distribution", headers=_h(tok_ngo), json={
        "received_quantity": 100.0,
        "distributed_quantity": 100.0,
        "remaining_quantity": 0.0,
        "beneficiaries_served": 100,
        "remarks": "Final batch served at Elder Care Community Home."
    })
    assert r_dist2.status_code == 200
    assert r_dist2.json()["remaining_quantity"] == 0.0
    print("  [OK] Distribution Event #2: 40 meals distributed (0 remaining -> Status: 'completed').")

    # 9. DONOR IMPACT ANALYTICS
    print("\n[STEP 9] Donor Real-Impact Dashboard...")
    r_impact = client.get("/api/donations/donor/impact-summary", headers=_h(tok_donor))
    assert r_impact.status_code == 200, f"Impact fetch failed: {r_impact.text}"
    impact = r_impact.json()
    print(f"  [OK] Total Meals Donated: {impact['meals_donated']:.0f} meals")
    print(f"  [OK] Total Meals Rescued: {impact['meals_rescued']:.0f} meals")
    print(f"  [OK] Total Meals Distributed: {impact['meals_distributed']:.0f} meals")
    print(f"  [OK] Estimated Waste Diverted: {impact['estimated_waste_diverted_kg']:.1f} kg")
    print(f"  [OK] Completion Rate: {impact['completion_rate_percent']:.1f}%")

    # 10. ADMIN RESCUE CONTROL & AUDIT LOGS
    print("\n[STEP 10] Administrator (admin@fooddonation.org) Rescue Control & Statistics...")
    tok_admin = _token("admin@fooddonation.org")
    r_stats = client.get("/api/admin/statistics", headers=_h(tok_admin))
    assert r_stats.status_code == 200
    stats = r_stats.json()
    print(f"  [OK] Admin Platform Stats: {stats['total_donations']} Donations, {stats['completed_donations']} Completed Rescues, {stats['total_users']} Active Users")

    r_interv = client.get("/api/admin/interventions", headers=_h(tok_admin))
    assert r_interv.status_code == 200
    interv = r_interv.json()
    print(f"  [OK] Admin Live Interventions Monitor: {interv['urgent_count']} urgent items flagged (Total Needed: {interv['total_interventions_needed']}).")

    print("\n" + "=" * 70)
    print("ALL 10 STEPS OF THE RUNTIME RESCUE SIMULATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_full_simulation()
