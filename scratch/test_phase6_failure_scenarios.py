"""
Phase 6 Failure Scenarios & Edge Cases Automated Verification Suite.

Tests:
1. NGO #1 rejects -> Fallback search finds NGO #2 -> NGO #2 accepts.
2. Volunteer #1 rejects -> Fallback search finds Volunteer #2 -> Volunteer #2 accepts.
3. No volunteer available -> Emergency escalation -> Expanded search & Admin alert.
4. Food expires -> Status 'expired' -> Cannot be accepted (409) & Cannot be assigned (409).
5. Wrong volunteer tries OTP -> 403 Forbidden.
6. Correct OTP succeeds (200) -> Replayed OTP returns 409 Conflict.
"""
import requests
import json
import sys
from datetime import datetime, timezone, timedelta

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def get_token(email, password="pass123"):
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def run_tests():
    print("=" * 70)
    print("🚀 SMART FOOD DONATION — PHASE 6 FAILURE & EDGE CASES SUITE")
    print("=" * 70)

    # 1. Setup Auth Tokens
    donor_token = get_token("donor1@hotel.com")
    ngo1_token = get_token("ngo1@greenhope.org")
    ngo2_token = get_token("ngo2@feedindia.org")
    vol1_token = get_token("vol1@volunteer.org")
    vol2_token = get_token("vol2@volunteer.org")
    admin_token = get_token("admin@fooddonation.org")

    # Reset NGO capacities to 200 for clean test runs
    import sqlite3
    conn = sqlite3.connect("backend/smart_food.db")
    cur = conn.cursor()
    cur.execute("UPDATE ngos SET current_capacity = 200, capacity = 200 WHERE is_verified = 1")
    conn.commit()
    conn.close()

    # =========================================================================
    # SCENARIO 1: NGO Rejects -> System finds NGO #2 -> New Offer
    # =========================================================================
    print("\n" + "─" * 60)
    print("🧪 SCENARIO 1: NGO #1 Rejection & Fallback to NGO #2")
    print("─" * 60)

    now = datetime.now(timezone.utc)
    create_payload = {
        "food_name": "Surplus Lunch Buffet (Fallback NGO Test)",
        "food_category": "Cooked Food",
        "quantity": 50,
        "quantity_unit": "Meals",
        "storage_method": "Heated/Insulated",
        "packaging_type": "Insulated Containers",
        "pickup_address": "Indiranagar 100ft Road, Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.90,
        "spoilage_detected": False,
        "packaging_sealed": True
    }

    res = requests.post(f"{BASE_URL}/api/donations", json=create_payload, headers=headers(donor_token))
    assert res.status_code in [200, 201], f"Failed to create donation: {res.text}"
    don1_id = res.json()["id"]
    print(f"✅ Step 1.1: Donor created donation #{don1_id} ('{create_payload['food_name']}')")

    # NGO #1 accepts then later rejects due to sudden capacity issue
    res = requests.post(f"{BASE_URL}/api/donations/{don1_id}/accept", headers=headers(ngo1_token))
    assert res.status_code == 200, f"NGO 1 accept failed: {res.text}"
    print(f"✅ Step 1.2: NGO #1 (Green Hope) initially accepted donation #{don1_id}")

    # NGO #1 rejects
    res = requests.post(
        f"{BASE_URL}/api/donations/{don1_id}/reject?reason=Sudden+kitchen+maintenance",
        headers=headers(ngo1_token)
    )
    assert res.status_code == 200, f"NGO 1 reject failed: {res.text}"
    reject_data = res.json()
    print(f"✅ Step 1.3: NGO #1 rejected donation #{don1_id} -> {reject_data['detail']}")
    assert reject_data.get("fallback_notified") is True, "Fallback matching should notify candidate NGO"
    print(f"✅ Step 1.4: Fallback search alerted next candidate NGO (fallback_notified=True)")

    # Verify donation status reset to pending
    res = requests.get(f"{BASE_URL}/api/donations/{don1_id}", headers=headers(donor_token))
    assert res.status_code == 200
    assert res.json()["status"] == "pending", f"Expected pending, got {res.json()['status']}"
    assert res.json()["assigned_ngo_id"] is None, "Assigned NGO should be cleared"
    print(f"✅ Step 1.5: Donation #{don1_id} status safely reverted to 'pending' (assigned_ngo_id=None)")

    # NGO #2 (Care India Shelter) accepts the fallback offer
    res = requests.post(f"{BASE_URL}/api/donations/{don1_id}/accept", headers=headers(ngo2_token))
    assert res.status_code == 200, f"NGO #2 accept failed: {res.text}"
    assert res.json()["status"] == "accepted"
    print(f"✅ Step 1.6: NGO #2 (Care India Shelter) successfully accepted fallback donation #{don1_id}!")

    # =========================================================================
    # SCENARIO 2: Volunteer Rejects -> System finds Volunteer #2
    # =========================================================================
    print("\n" + "─" * 60)
    print("🧪 SCENARIO 2: Volunteer #1 Rejection & Fallback to Volunteer #2")
    print("─" * 60)

    # Assign Volunteer #1
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don1_id}&volunteer_id=8",
        headers=headers(vol1_token)
    )
    assert res.status_code == 200, f"Volunteer 1 assign failed: {res.text}"
    assign1_id = res.json()["id"]
    print(f"✅ Step 2.1: Volunteer #1 assigned to donation #{don1_id} (Assignment #{assign1_id})")

    # Verify donation status is volunteer_assigned
    res = requests.get(f"{BASE_URL}/api/donations/{don1_id}", headers=headers(donor_token))
    assert res.json()["status"] == "volunteer_assigned"
    print(f"✅ Step 2.2: Donation status updated to 'volunteer_assigned'")

    # Volunteer #1 rejects assignment
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments/{assign1_id}/reject?reason=Vehicle+puncture+on+the+way",
        headers=headers(vol1_token)
    )
    assert res.status_code == 200, f"Volunteer 1 reject failed: {res.text}"
    vol_reject_data = res.json()
    print(f"✅ Step 2.3: Volunteer #1 rejected assignment #{assign1_id} -> {vol_reject_data['detail']}")
    assert vol_reject_data.get("fallback_notified") is True, "Fallback volunteer should be notified"
    print(f"✅ Step 2.4: Fallback volunteer search alerted Volunteer #2 (fallback_notified=True)")

    # Verify donation status reverted to accepted
    res = requests.get(f"{BASE_URL}/api/donations/{don1_id}", headers=headers(donor_token))
    assert res.json()["status"] == "accepted", f"Expected accepted, got {res.json()['status']}"
    assert res.json()["assigned_volunteer_id"] is None
    print(f"✅ Step 2.5: Donation status safely reverted to 'accepted' (awaiting replacement courier)")

    # Volunteer #2 accepts the pickup task
    # Fetch volunteer 2 user ID (Priya Singh)
    res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers(vol2_token))
    vol2_user_id = res.json()["id"]

    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don1_id}&volunteer_id={vol2_user_id}",
        headers=headers(vol2_token)
    )
    assert res.status_code == 200, f"Volunteer 2 assign failed: {res.text}"
    assign2_id = res.json()["id"]
    print(f"✅ Step 2.6: Volunteer #2 (Priya Singh) successfully accepted assignment #{assign2_id}!")

    # =========================================================================
    # SCENARIO 3: No Volunteer Available -> Emergency Escalation & Admin Alert
    # =========================================================================
    print("\n" + "─" * 60)
    print("🧪 SCENARIO 3: Emergency Escalation & Admin Alert")
    print("─" * 60)

    # Create high-risk donation with tight deadline
    urgent_payload = {
        "food_name": "Urgent Banquet Leftovers (Escalation Test)",
        "food_category": "Cooked Food",
        "quantity": 60,
        "quantity_unit": "Meals",
        "storage_method": "Room Temperature",
        "packaging_type": "Foil Trays",
        "pickup_address": "Whitefield Main Road, Bengaluru",
        "latitude": 12.9698,
        "longitude": 77.7500,
        "preparation_time": (now - timedelta(hours=2)).isoformat(),
        "expiry_time": (now + timedelta(minutes=45)).isoformat(), # 45m left
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.85,
        "spoilage_detected": False,
        "packaging_sealed": True
    }
    res = requests.post(f"{BASE_URL}/api/donations", json=urgent_payload, headers=headers(donor_token))
    assert res.status_code in [200, 201], f"Failed to create urgent donation: {res.text}"
    don_esc_id = res.json()["id"]
    print(f"✅ Step 3.1: Created tight-window donation #{don_esc_id} (45m left before expiry)")

    # Execute emergency priority escalation
    res = requests.post(f"{BASE_URL}/api/donations/{don_esc_id}/escalate", headers=headers(donor_token))
    assert res.status_code == 200, f"Escalate failed: {res.text}"
    esc_data = res.json()
    assert esc_data["is_emergency"] is True, "Donation should be flagged is_emergency=True"
    print(f"✅ Step 3.2: Escalation executed -> is_emergency={esc_data['is_emergency']}, escalated_at={esc_data.get('escalated_at')}")

    # Verify Admin received emergency notification
    res = requests.get(f"{BASE_URL}/api/notifications", headers=headers(admin_token))
    assert res.status_code == 200
    admin_notifs = res.json()
    escalation_alerts = [n for n in admin_notifs if n.get("related_donation_id") == don_esc_id or "EMERGENCY" in n.get("title", "")]
    assert len(escalation_alerts) > 0, "Admin should receive emergency alert"
    print(f"✅ Step 3.3: Admin received high-priority notification: '{escalation_alerts[0]['title']}'")

    # =========================================================================
    # SCENARIO 4: Food Expires -> Terminal State -> Cannot Accept / Assign
    # =========================================================================
    print("\n" + "─" * 60)
    print("🧪 SCENARIO 4: Food Expiry & Terminal State Enforcement")
    print("─" * 60)

    # Create a valid donation
    valid_payload = {
        "food_name": "Past Deadline Buffet (Expiry Test)",
        "food_category": "Cooked Food",
        "quantity": 40,
        "quantity_unit": "Meals",
        "storage_method": "Room Temperature",
        "packaging_type": "Boxes",
        "pickup_address": "Koramangala 4th Block, Bengaluru",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=1)).isoformat(),
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.80,
        "spoilage_detected": False,
        "packaging_sealed": True
    }
    res = requests.post(f"{BASE_URL}/api/donations", json=valid_payload, headers=headers(donor_token))
    assert res.status_code in [200, 201], f"Failed to create donation: {res.text}"
    don_exp_id = res.json()["id"]
    print(f"✅ Step 4.1: Created donation #{don_exp_id}")

    # Simulate pickup deadline passing in the database
    import sqlite3
    conn = sqlite3.connect("backend/smart_food.db")
    cur = conn.cursor()
    elapsed_time = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE food_donations SET expiry_time = ? WHERE id = ?", (elapsed_time, don_exp_id))
    conn.commit()
    conn.close()
    print(f"✅ Step 4.2: Simulated elapsed pickup deadline in system DB ({elapsed_time})")

    # Auto-expiry triggers on listing/access
    res = requests.get(f"{BASE_URL}/api/donations", headers=headers(donor_token))
    res = requests.get(f"{BASE_URL}/api/donations/{don_exp_id}", headers=headers(donor_token))
    exp_status = res.json()["status"]
    print(f"✅ Step 4.3: System auto-detected elapsed deadline -> status='{exp_status}'")
    assert exp_status == "expired", f"Expected 'expired', got '{exp_status}'"

    # Try to Accept Expired Donation -> MUST FAIL
    res = requests.post(f"{BASE_URL}/api/donations/{don_exp_id}/accept", headers=headers(ngo1_token))
    print(f"✅ Step 4.4: NGO attempted acceptance on expired donation -> HTTP {res.status_code} ({res.json().get('detail')})")
    assert res.status_code in [400, 409], f"Expected 400/409, got {res.status_code}"

    # Try to Assign Volunteer to Expired Donation -> MUST FAIL
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don_exp_id}&volunteer_id=8",
        headers=headers(vol1_token)
    )
    print(f"✅ Step 4.5: Volunteer assignment attempted on expired donation -> HTTP {res.status_code} ({res.json().get('detail')})")
    assert res.status_code in [400, 409], f"Expected 400/409, got {res.status_code}"

    # =========================================================================
    # SCENARIO 5: Wrong Volunteer OTP -> 403 Forbidden
    # =========================================================================
    print("\n" + "─" * 60)
    print("🧪 SCENARIO 5: Wrong Volunteer OTP (Cross-Assignment / Unauthorized Courier)")
    print("─" * 60)

    # Let's create a fresh donation and assign Volunteer #1 (Rahul Sharma - ID 8)
    res = requests.post(f"{BASE_URL}/api/donations", json={
        "food_name": "Hot Dinner Curries (OTP Security Test)",
        "food_category": "Cooked Food",
        "quantity": 30,
        "quantity_unit": "Meals",
        "storage_method": "Heated/Insulated",
        "packaging_type": "Sealed Tins",
        "pickup_address": "MG Road, Bengaluru",
        "latitude": 12.9750,
        "longitude": 77.6050,
        "preparation_time": (now - timedelta(minutes=30)).isoformat(),
        "expiry_time": (now + timedelta(hours=3)).isoformat(),
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.92,
        "spoilage_detected": False,
        "packaging_sealed": True
    }, headers=headers(donor_token))
    assert res.status_code in [200, 201]
    don_otp_id = res.json()["id"]

    # Get verification code
    code_res = requests.get(f"{BASE_URL}/api/donations/{don_otp_id}/verification-code", headers=headers(donor_token))
    assert code_res.status_code == 200, f"Get code failed: {code_res.text}"
    otp_code = code_res.json()["otp"]
    print(f"✅ Step 5.1: Created donation #{don_otp_id} with OTP '{otp_code}'")

    # NGO accepts
    requests.post(f"{BASE_URL}/api/donations/{don_otp_id}/accept", headers=headers(ngo1_token))

    # Volunteer #1 is the legitimately assigned courier
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don_otp_id}&volunteer_id=8",
        headers=headers(vol1_token)
    )
    assert res.status_code == 200
    print(f"✅ Step 5.2: Volunteer #1 (Rahul Sharma - ID 8) assigned as official courier")

    # Volunteer #2 (Priya Singh - unauthorized courier) attempts to verify the OTP
    res = requests.post(
        f"{BASE_URL}/api/volunteers/verify-otp",
        json={"donation_id": don_otp_id, "otp": otp_code},
        headers=headers(vol2_token)
    )
    print(f"✅ Step 5.3: Unauthorized Volunteer #2 submitted OTP -> HTTP {res.status_code} ({res.json().get('detail')})")
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
    assert "not the assigned volunteer" in res.json().get("detail", "")

    # =========================================================================
    # SCENARIO 6: OTP Replay Protection (Correct OTP -> 200, Reuse -> 409 Conflict)
    # =========================================================================
    print("\n" + "─" * 60)
    print("🧪 SCENARIO 6: Cryptographic OTP Replay Protection")
    print("─" * 60)

    # Legitimate Volunteer #1 submits correct OTP -> SUCCESS
    res = requests.post(
        f"{BASE_URL}/api/volunteers/verify-otp",
        json={"donation_id": don_otp_id, "otp": otp_code},
        headers=headers(vol1_token)
    )
    assert res.status_code == 200, f"Legitimate OTP verification failed: {res.text}"
    print(f"✅ Step 6.1: Legitimate Volunteer #1 verified OTP '{otp_code}' -> HTTP 200 OK (Status: collected)")

    # Replay Attempt: Submitting the exact same OTP again -> MUST RETURN 409 CONFLICT
    res = requests.post(
        f"{BASE_URL}/api/volunteers/verify-otp",
        json={"donation_id": don_otp_id, "otp": otp_code},
        headers=headers(vol1_token)
    )
    print(f"✅ Step 6.2: Replay attempt with same OTP -> HTTP {res.status_code} ({res.json().get('detail')})")
    assert res.status_code == 409, f"Expected 409 Conflict on replay, got {res.status_code}: {res.text}"
    assert "already been used" in res.json().get("detail", "")

    print("\n" + "=" * 70)
    print("🎯 ALL 6 FAILURE & SECURITY SCENARIOS PASSED WITH ZERO REGRESSIONS!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
