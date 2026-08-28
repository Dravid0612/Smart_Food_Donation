import requests
import json
import time
from datetime import datetime, timezone, timedelta

BASE_URL = "http://127.0.0.1:8000/api"

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_step(step_num, title, details=None):
    print(f"\n[STEP {step_num}] {title}")
    if details:
        if isinstance(details, dict):
            for k, v in details.items():
                print(f"   * {k}: {v}")
        elif isinstance(details, list):
            for item in details:
                print(f"   * {item}")
        else:
            print(f"   * {details}")

def run_live_demonstration():
    print_header("SMART DONOR SYSTEM -- LIVE END-TO-END DEMO EXECUTION")

    # 1. Health check
    try:
        r = requests.get("http://127.0.0.1:8000/")
        print_step(1, "Server Health Check", {
            "API Base": BASE_URL,
            "Root Response": r.json()
        })
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        return

    # 2. Authentication across all 4 roles
    donor_auth = requests.post(f"{BASE_URL}/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"}).json()
    donor_token = donor_auth["access_token"]

    ngo_auth = requests.post(f"{BASE_URL}/auth/login", json={"email": "ngo1@greenhope.org", "password": "pass123"}).json()
    ngo_token = ngo_auth["access_token"]

    vol_auth = requests.post(f"{BASE_URL}/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"}).json()
    vol_token = vol_auth["access_token"]

    admin_auth = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@fooddonation.org", "password": "admin123"}).json()
    admin_token = admin_auth["access_token"]

    print_step(2, "Strict Role-Based Authentication & JWT Tokens", {
        "Donor (Taj Hotel)": f"Authenticated (User ID: {donor_auth['user_id']})",
        "NGO (Green Hope)": f"Authenticated (User ID: {ngo_auth['user_id']})",
        "Volunteer (Rahul)": f"Authenticated (User ID: {vol_auth['user_id']})",
        "Admin": f"Authenticated (User ID: {admin_auth['user_id']})",
    })

    # 3. AI Food Vision & Condition Assessment
    headers_donor = {"Authorization": f"Bearer {donor_token}"}
    ai_form_data = {
        "food_category": "Cooked Food",
        "storage_method": "Heated/Insulated",
        "storage_duration_hours": "1.0",
        "packaging_condition": "Sealed / Covered"
    }
    ai_res = requests.post(f"{BASE_URL}/ai/analyze-food", data=ai_form_data, headers=headers_donor).json()
    print_step(3, "AI Vision Assessment & Metadata Decision Fusion", {
        "Food Detected": ai_res["food_detected"],
        "Visible Spoilage": ai_res["visible_spoilage"],
        "Visual Condition": ai_res["visual_condition"],
        "Confidence Score": f"{ai_res['confidence'] * 100:.1f}%",
        "Overall Condition Score": f"{ai_res['condition_score']} / 100",
        "Safety Warning": ai_res["warning"]
    })

    # 4. Donor posts surplus food
    now = datetime.now(timezone.utc)
    headers_donor = {"Authorization": f"Bearer {donor_token}"}
    don_payload = {
        "food_name": "Taj Grand Buffet Surplus Meals",
        "food_category": "Cooked Food",
        "quantity": 50.0,
        "quantity_unit": "Meals",
        "preparation_time": (now - timedelta(hours=1)).isoformat(),
        "expiry_time": (now + timedelta(hours=6)).isoformat(),
        "pickup_address": "Taj Hotel MG Road, Bangalore",
        "storage_method": "Heated/Insulated",
        "storage_duration_hours": 1.0,
        "packaging_condition": "Sealed / Covered",
        "ai_visual_condition": ai_res["visual_condition"],
        "ai_confidence_score": ai_res["confidence"],
        "condition_score": ai_res["condition_score"]
    }
    don_res = requests.post(f"{BASE_URL}/donations", json=don_payload, headers=headers_donor).json()
    donation_id = don_res["id"]
    print_step(4, "Donation Created & Secure Verification Tokens Issued", {
        "Donation ID": donation_id,
        "Food Name": don_res["food_name"],
        "Quantity": f"{don_res['quantity']} {don_res['quantity_unit']}",
        "Status": don_res["status"],
        "Pickup Address": don_res["pickup_address"],
        "Urgency Level": don_res["urgency_level"]
    })

    # Retrieve secure OTP and QR code
    code_res = requests.get(f"{BASE_URL}/donations/{donation_id}/verification-code", headers=headers_donor).json()
    otp = code_res["otp"]
    qr_token = code_res["qr_token"]
    print(f"   * Generated 6-Digit Handover OTP: {otp}")
    print(f"   * Generated Cryptographic QR Token: {qr_token}")

    # 5. Smart NGO Matching & Acceptance
    headers_ngo = {"Authorization": f"Bearer {ngo_token}"}
    recs = requests.get(f"{BASE_URL}/donations/{donation_id}/recommend-ngo", headers=headers_ngo).json()
    top_ngo = recs[0]
    print_step(5, "Smart NGO Matching Engine Recommendation", {
        "Recommended NGO": top_ngo["organization_name"],
        "Match Score": f"{top_ngo['score']:.1f}%",
        "Distance": f"{top_ngo['distance_km']} km",
        "Operating Status": "OPEN NOW" if top_ngo["is_open_now"] else "CLOSED",
        "Recommendation Reason": top_ngo["reason"]
    })

    accept_res = requests.post(f"{BASE_URL}/donations/{donation_id}/accept", headers=headers_ngo).json()
    print(f"   * NGO Acceptance Result: Status -> {accept_res['status']}")

    # 6. Volunteer 5-Factor Recommendation & Assignment
    headers_vol = {"Authorization": f"Bearer {vol_token}"}
    vol_recs = requests.get(f"{BASE_URL}/donations/{donation_id}/recommend-volunteer", headers=headers_donor).json()
    top_vol = vol_recs[0]
    print_step(6, "5-Factor Volunteer Dispatch Matching", {
        "Assigned Volunteer": top_vol["volunteer_name"],
        "Vehicle Type": top_vol["vehicle_type"],
        "Carrying Capacity": f"{top_vol['carrying_capacity']} meals",
        "Reliability Score": f"{top_vol['reliability_score']}%",
        "Dispatch Score": f"{top_vol['score']:.1f}%",
        "Score Breakdown": str(top_vol["score_breakdown"])
    })

    assign_res = requests.post(
        f"{BASE_URL}/volunteers/assignments?donation_id={donation_id}&volunteer_id={vol_auth['user_id']}",
        headers=headers_vol
    ).json()
    print(f"   * Assignment Status: {assign_res['status']}")

    # 7. Handover OTP Verification (Server-Side)
    print_step(7, "Volunteer Pickup & Server-Side OTP Verification")
    # Verify with correct OTP
    verify_res = requests.post(
        f"{BASE_URL}/volunteers/verify-otp",
        json={"donation_id": donation_id, "otp": otp},
        headers=headers_vol
    ).json()
    print(f"   * Handover Confirmed! Status -> {verify_res['status']}")
    print(f"   * Volunteer safely collected {don_res['quantity']} {don_res['quantity_unit']}.")

    # 8. Volunteer Delivers Food to NGO
    deliver_res = requests.post(f"{BASE_URL}/donations/{donation_id}/deliver", headers=headers_vol).json()
    print_step(8, "Volunteer Delivery & Final Completion", {
        "Status": deliver_res["status"],
        "Assigned NGO ID": deliver_res["assigned_ngo_id"],
        "Updated At": deliver_res["updated_at"]
    })

    # 9. Verifiable Certificate of Participation
    cert = requests.get(f"{BASE_URL}/donations/{donation_id}/certificate", headers=headers_donor).json()
    print_step(9, "Generated Verifiable Certificate of Participation", {
        "Certificate ID": cert["certificate_id"],
        "Title": cert["title"],
        "Presented To": cert["donor_name"],
        "Food Rescued": f"{cert['quantity']} {cert['quantity_unit']} of {cert['food_name']}",
        "Receiving NGO": cert["receiving_ngo"],
        "CO2 Avoided": f"{cert['co2_saved_kg']} kg",
        "Water Saved": f"{cert['water_saved_liters']} Liters",
        "Verification Hash": cert["verification_hash"],
        "Official Disclaimer": cert["disclaimer"]
    })

    # 10. CSR Impact & Waste Disposal Cost-Avoidance Report
    csr = requests.get(f"{BASE_URL}/donations/csr/summary", headers=headers_donor).json()
    print_step(10, "Corporate CSR Impact & Cost-Avoided Insights", {
        "Donor Name": csr["donor_name"],
        "Total Completed Donations": csr["total_donations"],
        "Total Meals Donated": csr["total_meals_donated"],
        "Total CO2 Avoided": f"{csr['total_co2_avoided_kg']} kg",
        "Total Water Conserved": f"{csr['total_water_conserved_liters']} L",
        "Estimated Disposal Cost Avoided": f"INR {csr['estimated_disposal_cost_avoided_inr']:,.2f}",
        "Verified Partner NGOs Reached": csr["verified_ngo_partners_count"],
        "Donor Trust Score": f"{csr['trust_score']}%"
    })

    # 11. Two-Way Trust Ratings
    rate_res = requests.post(
        f"{BASE_URL}/donations/{donation_id}/rate",
        json={
            "donation_id": donation_id,
            "to_user_id": ngo_auth["user_id"],
            "role_to": "ngo",
            "rating_score": 5,
            "feedback": "Green Hope received the surplus food with verified temperature check.",
            "tags": "Professional, Dignified Handover, On-time"
        },
        headers=headers_donor
    ).json()
    print_step(11, "Two-Way Trust Rating Feedback", {
        "Rated User ID": rate_res["to_user_id"],
        "Role": rate_res["role_to"],
        "Rating Score": f"{rate_res['rating_score']} / 5 Stars",
        "Feedback": rate_res["feedback"],
        "Tags": rate_res["tags"]
    })

    # 12. Admin Statistics & Platform Heatmap
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    stats = requests.get(f"{BASE_URL}/admin/statistics", headers=headers_admin).json()
    heatmap = requests.get(f"{BASE_URL}/admin/waste-heatmap", headers=headers_admin).json()
    clusters = heatmap.get("clusters", [])
    sample_info = f"Cluster at Lat {clusters[0]['latitude']}, Lon {clusters[0]['longitude']} ({clusters[0]['total_meals']} meals, {clusters[0]['total_donations']} donations)" if clusters else "N/A"
    print_step(12, "Platform Administrator Analytics & Spatial Heatmap", {
        "Total Registered Users": stats["total_users"],
        "Total Meals Rescued": f"{stats['meals_donated']:.0f} meals",
        "Completed Donations": stats["completed_donations"],
        "Surplus Hotspots Clustered": f"{heatmap.get('total_clusters', len(clusters))} spatial cluster zones",
        "Total Surplus Impact Meals": f"{heatmap.get('total_impacted_meals', 0)} meals",
        "Sample Cluster Zone": sample_info
    })

    print_header("DEMONSTRATION COMPLETED SUCCESSFULLY -- 100% VERIFIED!")

if __name__ == "__main__":
    run_live_demonstration()
