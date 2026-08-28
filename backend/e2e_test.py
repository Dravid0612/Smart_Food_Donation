"""Complete E2E workflow test for Smart Donor backend"""
import requests, datetime as dt_mod, sys

BASE = 'http://127.0.0.1:8000/api'

def L(email, pw):
    r = requests.post(f'{BASE}/auth/login', json={'email': email, 'password': pw})
    return r.json()['access_token']

def H(tok):
    return {'Authorization': f'Bearer {tok}'}

at = L('admin@fooddonation.org', 'admin123')
dt = L('donor1@hotel.com', 'pass123')
nt = L('ngo1@greenhope.org', 'pass123')
vt = L('vol3@volunteer.org', 'pass123')
print("All 4 roles logged in OK")
print(f"  admin={at[:20]}... donor={dt[:20]}... ngo={nt[:20]}... vol={vt[:20]}...")

# Create donation
now = dt_mod.datetime.now(dt_mod.timezone.utc)
don = requests.post(f'{BASE}/donations', headers=H(dt), json={
    'food_name': 'E2E Test Rice Curry',
    'food_category': 'Cooked Food',
    'quantity': 75,
    'quantity_unit': 'Meals',
    'preparation_time': (now - dt_mod.timedelta(hours=1)).isoformat(),
    'expiry_time': (now + dt_mod.timedelta(hours=3)).isoformat(),
    'pickup_address': 'MG Road Test Hotel, Bangalore',
    'latitude': 12.975,
    'longitude': 77.608
})
don_id = don.json()['id']
print(f"Donation: {don.status_code} id={don_id} status={don.json().get('status')}")

# AI Analysis
ai = requests.post(f'{BASE}/ai/analyze-food', headers=H(dt), json={
    'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Kumato_tomato_cross_section.jpg/800px-Kumato_tomato_cross_section.jpg',
    'food_name': 'Rice and Curry',
    'food_category': 'Cooked Food'
})
aij = ai.json()
print(f"AI Analysis: {ai.status_code}")
print(f"  visual_condition={aij.get('visual_condition')} confidence={aij.get('confidence')}")
print(f"  visible_spoilage={aij.get('visible_spoilage')}")
obs = aij.get('observations', [])
print(f"  observation[0]={obs[0][:100] if obs else 'N/A'}")
# Safety claim check
resp_str = str(aij).lower()
bad_claims = ['ai says food is safe', 'safe to eat', 'safe to consume']
found = [c for c in bad_claims if c in resp_str]
print(f"  Safety claim check: {'FAIL - ' + str(found) if found else 'PASS - no unsafe safety guarantees'}")

# NGO Matching
nm = requests.get(f'{BASE}/donations/{don_id}/recommend-ngo', headers=H(dt))
ngos = nm.json()
print(f"NGO Match: {nm.status_code} count={len(ngos)}")
for i, n in enumerate(ngos[:3]):
    print(f"  Rank {i+1}: {n.get('organization_name', '?'):<25} score={n.get('match_score', '?')}")
names = [n.get('organization_name', '') for n in ngos]
gh_rank = next((i for i, n in enumerate(names) if 'Green Hope' in n), -1)
sh_rank = next((i for i, n in enumerate(names) if 'Share' in n), -1)
if gh_rank >= 0 and sh_rank >= 0:
    print(f"  Green Hope rank={gh_rank+1}, Share A Meal rank={sh_rank+1}")
    print(f"  Demand-match ranking: {'CORRECT' if gh_rank < sh_rank else 'UNEXPECTED'}")

# Volunteer Matching (75 meals - should exclude low capacity)
vm = requests.get(f'{BASE}/donations/{don_id}/recommend-volunteer', headers=H(dt))
vols = vm.json()
print(f"Vol Match: {vm.status_code} count={len(vols)}")
for i, v in enumerate(vols[:4]):
    print(f"  Vol {i+1}: type={v.get('vehicle_type','?'):<6} cap={v.get('vehicle_capacity','?')}")
under = [v for v in vols if isinstance(v.get('vehicle_capacity'), (int,float)) and v.get('vehicle_capacity', 999) < 75]
print(f"  Under-capacity in results: {'FAIL' if under else 'PASS - all have sufficient capacity'}")

# NGO Accept
na = requests.post(f'{BASE}/donations/{don_id}/accept', headers=H(nt))
print(f"NGO Accept: {na.status_code} status={na.json().get('status', '?')}")

# Duplicate NGO Accept check
na2 = requests.post(f'{BASE}/donations/{don_id}/accept', headers=H(nt))
print(f"Duplicate Accept: {na2.status_code} (PASS if 409)")

# Volunteer Assign
me_v = requests.get(f'{BASE}/auth/me', headers=H(vt))
vol_id = me_v.json()['id']
va = requests.post(f'{BASE}/volunteers/assignments?donation_id={don_id}&volunteer_id={vol_id}', headers=H(vt))
print(f"Vol Assign: {va.status_code}")

# Capacity gate - bike (cap=50) should be blocked for 75-meal donation
vol1_t = L('vol1@volunteer.org', 'pass123')
vol1_me = requests.get(f'{BASE}/auth/me', headers=H(vol1_t))
vol1_id = vol1_me.json()['id']
va_blocked = requests.post(f'{BASE}/volunteers/assignments?donation_id={don_id}&volunteer_id={vol1_id}', headers=H(vol1_t))
print(f"Capacity gate (bike cap=50 -> 75 meals): {va_blocked.status_code} (PASS if 409)")

# Get OTP from donor
otp_r = requests.get(f'{BASE}/donations/{don_id}/verification-code', headers=H(dt))
otp_val = otp_r.json().get('otp')
print(f"OTP retrieved: {otp_r.status_code} otp={otp_val}")

# OTP Verify
if otp_val:
    ov = requests.post(f'{BASE}/volunteers/verify-otp', headers=H(vt),
                       json={'donation_id': don_id, 'otp': otp_val})
    print(f"OTP Verify: {ov.status_code} => {ov.json().get('message', ov.text[:80])}")

    # Anti-replay
    ov2 = requests.post(f'{BASE}/volunteers/verify-otp', headers=H(vt),
                        json={'donation_id': don_id, 'otp': otp_val})
    print(f"OTP Replay: {ov2.status_code} (PASS if 409)")

# Collect & Deliver
col = requests.post(f'{BASE}/donations/{don_id}/collect', headers=H(vt), json={})
print(f"Collect: {col.status_code}")
dlv = requests.post(f'{BASE}/donations/{don_id}/deliver', headers=H(vt), json={})
print(f"Deliver: {dlv.status_code}")

# Distribution
dis = requests.post(f'{BASE}/donations/{don_id}/distribution', headers=H(nt),
                    json={'distributed_quantity': 30.0, 'received_quantity': 75.0, 'remaining_quantity': 45.0, 'beneficiaries_served': 30, 'remarks': '30 families served'})
print(f"Distribution: {dis.status_code} {dis.text[:100]}")

# Donor impact metrics
dm = requests.get(f'{BASE}/donations/metrics/summary', headers=H(dt))
dj = dm.json()
print(f"Donor Metrics: {dm.status_code}")
print(f"  meals_donated={dj.get('meals_donated')} meals_rescued={dj.get('meals_rescued')} completed_rescues={dj.get('completed_rescues_count')}")

# Certificate
cert = requests.get(f'{BASE}/donations/{don_id}/certificate', headers=H(dt))
print(f"Certificate: {cert.status_code} content-type={cert.headers.get('content-type', '?')[:50]}")

# Admin stats
adm = requests.get(f'{BASE}/admin/statistics', headers=H(at))
aj = adm.json()
print(f"Admin Stats: {adm.status_code} users={aj.get('total_users')} donations={aj.get('total_donations')}")

# Role guard
rg = requests.get(f'{BASE}/admin/statistics', headers=H(dt))
print(f"Role Guard: donor->admin/statistics = {rg.status_code} (PASS if 403)")

# Urgent escalation check
urg_don = requests.post(f'{BASE}/donations', headers=H(dt), json={
    'food_name': 'Urgent Expiring Food',
    'food_category': 'Cooked Food',
    'quantity': 20,
    'quantity_unit': 'Meals',
    'preparation_time': (now - dt_mod.timedelta(hours=1)).isoformat(),
    'expiry_time': (now + dt_mod.timedelta(minutes=45)).isoformat(),
    'pickup_address': 'Urgent Address, Bangalore',
    'latitude': 12.976,
    'longitude': 77.609,
})
if urg_don.status_code == 201:
    urg_id = urg_don.json()['id']
    urg_detail = requests.get(f'{BASE}/donations/{urg_id}', headers=H(dt))
    urd = urg_detail.json()
    print(f"Urgent (45min): status={urd.get('status')} urgency={urd.get('urgency_level')}")

print()
print("=" * 50)
print("ALL E2E TESTS COMPLETE")
