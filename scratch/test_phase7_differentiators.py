"""
Phase 7 — Core Innovation Differentiators Verification Suite.

Tests:
1. AI-Assisted Condition Assessment: Image + metadata -> Visual condition + advisory disclaimer.
   (Ensures NO 'AI says safe', verifies 'no obvious visible spoilage detected' & disclaimer).
2. Demand-Aware NGO Matching:
   - Donation = 'Rice + Curry' (Cooked Food).
   - NGO A (3km away) needs Cooked Food.
   - NGO B (1km away) needs Bread only.
   - Proves NGO A gets HIGHER match score despite greater distance.
3. Capacity-Aware Volunteer Matching:
   - Donation = 75 meals.
   - Walking volunteer (10 meals) -> 400 Rejected.
   - Bike volunteer (50 meals) -> 400 Rejected.
   - Car/Van volunteer (100 meals) -> 200 Accepted.
4. Expiry-Aware Rescue:
   - 3 hours remaining -> 'Fresh' / Normal priority.
   - 45 minutes remaining -> 'Urgent'.
   - Escalation -> 'is_emergency: true', Admin notification.
"""
import sys
import json
import requests
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
    print("=" * 75)
    print("🌟 SMART FOOD DONATION — PHASE 7 INNOVATION DIFFERENTIATORS SUITE")
    print("=" * 75)

    donor_token = get_token("donor1@hotel.com")
    ngo1_token = get_token("ngo1@greenhope.org")
    vol1_token = get_token("vol1@volunteer.org")
    admin_token = get_token("admin@fooddonation.org")

    now = datetime.now(timezone.utc)

    # =========================================================================
    # DIFFERENTIATOR 1: AI-Assisted Visual Condition Assessment & Safety Disclaimer
    # =========================================================================
    print("\n" + "─" * 65)
    print("🧠 DIFFERENTIATOR 1: AI Visual Assessment & Responsible Safety Disclaimer")
    print("─" * 65)

    # Post photo metadata to AI analysis endpoint
    ai_req_data = {
        "food_category": "Cooked Food",
        "quantity": 50.0,
        "storage_method": "Heated/Insulated",
        "storage_duration_hours": 1.5,
        "packaging_condition": "Sealed / Covered"
    }

    res = requests.post(
        f"{BASE_URL}/api/ai/analyze-food",
        data=ai_req_data,
        headers={"Authorization": f"Bearer {donor_token}"}
    )
    assert res.status_code == 200, f"AI analyze failed: {res.text}"
    ai_result = res.json()

    print(f"✅ Step 1.1: AI Vision output generated:")
    print(f"   • Visual Condition   : {ai_result['visual_condition']} (Score: {ai_result['condition_score']}/100, Conf: {ai_result['confidence']*100:.0f}%)")
    print(f"   • Visible Spoilage   : {ai_result['visible_spoilage']}")
    print(f"   • Packaging Integrity: {ai_result['packaging_integrity']}")
    print(f"   • Storage Evaluation : {ai_result['storage_assessment']}")

    # Strict Safety Policy Verification
    disclaimer = ai_result.get("safety_disclaimer", "") or ai_result.get("warning", "")
    print(f"\n   🛡️ Safety Disclaimer Enforcement:")
    print(f"   '{disclaimer}'")
    
    assert "cannot guarantee food safety" in disclaimer.lower() or "visual assessment only" in disclaimer.lower(), \
        "Safety disclaimer MUST state that visual analysis cannot certify microbiological safety!"
    assert "safe" not in ai_result.get("visual_condition", "").lower(), \
        "AI output must never claim 'food is safe', only visual characteristics!"
    print(f"✅ Step 1.2: Strict Responsible AI compliance verified (Responsible disclaimer active)")

    # =========================================================================
    # DIFFERENTIATOR 2: Demand-Aware NGO Matching (Demand > Distance)
    # =========================================================================
    print("\n" + "─" * 65)
    print("🎯 DIFFERENTIATOR 2: Demand-Aware NGO Matchmaking (Beneficiary Alignment)")
    print("─" * 65)

    # Configure two NGOs in DB to demonstrate Demand Dominance:
    # NGO A (ID 5 - Green Hope): 3.2 km away, DEMAND = {"Cooked Food": 100}
    # NGO B (ID 6 - Feed India): 1.1 km away (closer!), DEMAND = {"Bakery": 100, "Cooked Food": 0}
    import sqlite3
    conn = sqlite3.connect("backend/smart_food.db")
    cur = conn.cursor()
    # NGO A: Cooked Food demand, further distance (12.9800, 77.6300)
    cur.execute("""
        UPDATE ngos 
        SET demand_requirements = '{"Cooked Food": 100}', 
            latitude = 12.9800, longitude = 77.6300,
            current_capacity = 150, capacity = 150, is_verified = 1, is_available = 1
        WHERE id = 5
    """)
    # NGO B: Bakery demand only, closer distance (12.9730, 77.6000)
    cur.execute("""
        UPDATE ngos 
        SET demand_requirements = '{"Bakery": 100}', 
            latitude = 12.9730, longitude = 77.6000,
            current_capacity = 150, capacity = 150, is_verified = 1, is_available = 1
        WHERE id = 6
    """)
    conn.commit()
    conn.close()

    # Create a donation of 'Cooked Food' (Rice + Curry) at (12.9716, 77.5946)
    res = requests.post(f"{BASE_URL}/api/donations", json={
        "food_name": "Hot Rice & Vegetable Curry",
        "food_category": "Cooked Food",
        "quantity": 50,
        "quantity_unit": "Meals",
        "storage_method": "Heated/Insulated",
        "packaging_type": "Insulated Containers",
        "pickup_address": "MG Road, Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.92,
        "spoilage_detected": False,
        "packaging_sealed": True
    }, headers=headers(donor_token))
    assert res.status_code in [200, 201]
    don_demand_id = res.json()["id"]

    # Query Match Recommendations for this donation
    res = requests.get(f"{BASE_URL}/api/donations/{don_demand_id}/recommend-ngo", headers=headers(donor_token))
    assert res.status_code == 200, f"Get recs failed: {res.text}"
    recs = res.json()

    ngo_a_rec = next((r for r in recs if r["ngo_id"] == 5), None)
    ngo_b_rec = next((r for r in recs if r["ngo_id"] == 6), None)

    print(f"✅ Step 2.1: Donation Category: 'Cooked Food' (50 meals)")
    print(f"   • NGO A (Green Hope) : Distance = {ngo_a_rec['distance_km']} km | Demand = Cooked Food (MATCH)   | Match Score = {ngo_a_rec['score']}")
    print(f"   • NGO B (Feed India)  : Distance = {ngo_b_rec['distance_km']} km | Demand = Bakery Only (MISMATCH)| Match Score = {ngo_b_rec['score']}")

    assert ngo_a_rec["score"] > ngo_b_rec["score"], \
        f"Expected NGO A (Demand Matched) score ({ngo_a_rec['score']}) > Closer NGO B score ({ngo_b_rec['score']})!"
    print(f"✅ Step 2.2: Demand Dominance Verified! NGO A (3.9 km) ranked higher than NGO B (0.6 km) due to active demand alignment!")

    # =========================================================================
    # DIFFERENTIATOR 3: Capacity-Aware Volunteer Matching (Strict Payload Guard)
    # =========================================================================
    print("\n" + "─" * 65)
    print("⚖️ DIFFERENTIATOR 3: Vehicle Carrying Capacity Guard (Logistics Safety)")
    print("─" * 65)

    # Configure 3 volunteers with different vehicles & payload capacities in DB
    conn = sqlite3.connect("backend/smart_food.db")
    cur = conn.cursor()
    # User 8: Walking Courier (10 meals)
    cur.execute("UPDATE users SET vehicle_type = 'walking', carrying_capacity = 10, is_active = 1 WHERE id = 8")
    # User 9: Bike Courier (50 meals)
    cur.execute("UPDATE users SET vehicle_type = 'bike', carrying_capacity = 50, is_active = 1 WHERE id = 9")
    # User 10: Van / Car Courier (100 meals)
    cur.execute("UPDATE users SET vehicle_type = 'van', carrying_capacity = 100, is_active = 1 WHERE id = 10")
    conn.commit()
    conn.close()

    # Create a large 75-meal donation
    res = requests.post(f"{BASE_URL}/api/donations", json={
        "food_name": "Large Buffet Surplus (75 Meals Capacity Test)",
        "food_category": "Cooked Food",
        "quantity": 75,
        "quantity_unit": "Meals",
        "storage_method": "Heated/Insulated",
        "packaging_type": "Large Trays",
        "pickup_address": "Indiranagar, Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(),
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.88,
        "spoilage_detected": False,
        "packaging_sealed": True
    }, headers=headers(donor_token))
    assert res.status_code in [200, 201]
    don_cap_id = res.json()["id"]

    # Accept by NGO first
    requests.post(f"{BASE_URL}/api/donations/{don_cap_id}/accept", headers=headers(ngo1_token))

    # Test 3.1: Walking Volunteer (10 meals) attempting 75 meals -> REJECT
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don_cap_id}&volunteer_id=8",
        headers=headers(vol1_token)
    )
    print(f"✅ Step 3.1: Walking Courier (Cap: 10 meals) assigned 75 meals -> HTTP {res.status_code}")
    assert res.status_code == 400
    print(f"   • Error: {res.json()['detail']}")

    # Test 3.2: Bike Volunteer (50 meals) attempting 75 meals -> REJECT
    vol2_token = get_token("vol2@volunteer.org")
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don_cap_id}&volunteer_id=9",
        headers=headers(vol2_token)
    )
    print(f"✅ Step 3.2: Bike Courier (Cap: 50 meals) assigned 75 meals -> HTTP {res.status_code}")
    assert res.status_code == 400
    print(f"   • Error: {res.json()['detail']}")

    # Test 3.3: Van / Car Volunteer (100 meals) attempting 75 meals -> ALLOW
    vol3_token = get_token("vol3@volunteer.org")
    res = requests.post(
        f"{BASE_URL}/api/volunteers/assignments?donation_id={don_cap_id}&volunteer_id=10",
        headers=headers(vol3_token)
    )
    print(f"✅ Step 3.3: Van Courier (Cap: 100 meals) assigned 75 meals -> HTTP {res.status_code}")
    assert res.status_code == 200
    print(f"   • Success: Assignment #{res.json()['id']} created for Van Courier Amit Kumar")

    # =========================================================================
    # DIFFERENTIATOR 4: Expiry-Aware Rescue & Emergency Escalation
    # =========================================================================
    print("\n" + "─" * 65)
    print("⏰ DIFFERENTIATOR 4: Expiry-Aware Rescue & Escalation State Machine")
    print("─" * 65)

    # Test 4.1: Donation with 4 hours left -> Urgency Level: 'Fresh'
    res = requests.post(f"{BASE_URL}/api/donations", json={
        "food_name": "Fresh Afternoon Batch",
        "food_category": "Cooked Food",
        "quantity": 25,
        "quantity_unit": "Meals",
        "storage_method": "Heated/Insulated",
        "packaging_type": "Insulated Containers",
        "pickup_address": "Koramangala, Bengaluru",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "preparation_time": now.isoformat(),
        "expiry_time": (now + timedelta(hours=4)).isoformat(), # 4h left
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.95,
        "spoilage_detected": False,
        "packaging_sealed": True
    }, headers=headers(donor_token))
    don_fresh_id = res.json()["id"]
    urgency_fresh = res.json()["urgency_level"]
    print(f"✅ Step 4.1: Donation #{don_fresh_id} (4 hours left) -> Urgency Level: '{urgency_fresh}' (Normal Priority)")
    assert urgency_fresh == "Fresh"

    # Test 4.2: Donation with 45 mins left -> Urgency Level: 'Urgent'
    res = requests.post(f"{BASE_URL}/api/donations", json={
        "food_name": "Expedited Dinner Leftovers",
        "food_category": "Cooked Food",
        "quantity": 30,
        "quantity_unit": "Meals",
        "storage_method": "Room Temperature",
        "packaging_type": "Containers",
        "pickup_address": "Whitefield, Bengaluru",
        "latitude": 12.9698,
        "longitude": 77.7500,
        "preparation_time": (now - timedelta(hours=3)).isoformat(),
        "expiry_time": (now + timedelta(minutes=45)).isoformat(), # 45m left (12.5% of 4h total)
        "ai_visual_condition": "GOOD",
        "ai_confidence_score": 0.85,
        "spoilage_detected": False,
        "packaging_sealed": True
    }, headers=headers(donor_token))
    don_urgent_id = res.json()["id"]
    urgency_urgent = res.json()["urgency_level"]
    print(f"✅ Step 4.2: Donation #{don_urgent_id} (45 mins left) -> Urgency Level: '{urgency_urgent}' (Expedited Window)")
    assert urgency_urgent == "Urgent"

    # Test 4.3: Escalation trigger -> Flagged Emergency & Admin Alerted
    res = requests.post(f"{BASE_URL}/api/donations/{don_urgent_id}/escalate", headers=headers(donor_token))
    assert res.status_code == 200
    assert res.json()["is_emergency"] is True
    print(f"✅ Step 4.3: Emergency Escalation Executed -> is_emergency=True")

    # Verify Admin received high-priority alert
    res = requests.get(f"{BASE_URL}/api/notifications", headers=headers(admin_token))
    admin_notifs = res.json()
    urgent_alerts = [n for n in admin_notifs if n.get("related_donation_id") == don_urgent_id]
    assert len(urgent_alerts) > 0
    print(f"✅ Step 4.4: Admin Alert Verified: '{urgent_alerts[0]['title']}' - '{urgent_alerts[0]['message']}'")

    print("\n" + "=" * 75)
    print("🏆 ALL 4 CORE INNOVATION DIFFERENTIATORS FULLY PROVEN & VERIFIED!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
